from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.db.manager import history_manager
from app.models.history_request import HistoryCreate, HistoryUpdateById, HistoryUpdateByPair
from app.models.history_response import HistoryOut

router = APIRouter(prefix="/history", tags=["history"])


@router.post("", response_model=HistoryOut)
def create_history(payload: HistoryCreate, db: Session = Depends(get_db)):
    """히스토리 레코드 생성.

    규칙:
        클라이언트가 to_user_id와 target_user_id만 제공한 경우(다른 필드가 설정되지 않음),
        모든 결과 필드는 'pending'으로 설정하고 해당 타임스탬프는 None으로 유지합니다.
    """
    # Detect fields explicitly provided by client
    provided = payload.dict(exclude_unset=True)
    # If only to_user_id and target_user_id were provided, enforce defaults/time-null as requested
    if set(provided.keys()) <= {"to_user_id", "target_user_id"}:
        mh = history_manager.create(
            db,
            to_user_id=payload.to_user_id,
            target_user_id=payload.target_user_id,
            proposal_result="pending",
            counterpart_result="pending",
            final_result="pending",
            timestamps={
                "proposal_result_at": None,
                "counterpart_result_at": None,
                "final_result_at": None,
            },
        )
    else:
        # Use provided values (pydantic already filled defaults for absent fields)
        mh = history_manager.create(
            db,
            to_user_id=payload.to_user_id,
            target_user_id=payload.target_user_id,
            proposal_result=payload.proposal_result,
            counterpart_result=payload.counterpart_result,
            final_result=payload.final_result,
            timestamps={
                "proposal_result_at": payload.proposal_result_at,
                "counterpart_result_at": payload.counterpart_result_at,
                "final_result_at": payload.final_result_at,
            },
        )
    return mh


@router.get("", response_model=List[HistoryOut])
def list_histories(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return history_manager.list_all(db, skip=skip, limit=limit)


@router.get("/{id}", response_model=HistoryOut)
def get_history(id: int, db: Session = Depends(get_db)):
    mh = history_manager.get_by_id(db, id)
    if mh is None:
        raise HTTPException(status_code=404, detail="history not found")
    return mh


@router.get("/by-to/{to_user_id}", response_model=List[HistoryOut])
def list_by_to(to_user_id: int, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return history_manager.list_by_to_user(db, to_user_id=to_user_id, skip=skip, limit=limit)


@router.get("/by-target/{target_user_id}", response_model=List[HistoryOut])
def list_by_target(
    target_user_id: int, skip: int = 0, limit: int = 50, db: Session = Depends(get_db)
):
    return history_manager.list_by_target_user(
        db, target_user_id=target_user_id, skip=skip, limit=limit
    )


@router.get("/pending/proposal", response_model=List[HistoryOut])
def pending_proposal(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return history_manager.list_by_status(db, proposal="pending", skip=skip, limit=limit)


@router.get("/pending/counterpart", response_model=List[HistoryOut])
def pending_counterpart(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return history_manager.list_by_status(db, counterpart="pending", skip=skip, limit=limit)


@router.get("/pending/final", response_model=List[HistoryOut])
def pending_final(skip: int = 0, limit: int = 50, db: Session = Depends(get_db)):
    return history_manager.list_by_status(db, final="pending", skip=skip, limit=limit)


@router.patch("/{id}", response_model=HistoryOut)
def patch_by_id(id: int, payload: HistoryUpdateById, db: Session = Depends(get_db)):
    """ID로 특정 결과 필드들을 업데이트합니다.

    동작:
        제공된 결과 필드가 있으나 해당 타임스탬프가 없으면
        history_manager.update_results가 현재 UTC 시간을 타임스탬프에 설정합니다.
    """
    # Convert pydantic model to kwargs (keeping None for unset fields)
    data = payload.dict(exclude_unset=True)
    try:
        mh = history_manager.update_results(
            db,
            id,
            proposal_result=data.get("proposal_result"),
            counterpart_result=data.get("counterpart_result"),
            final_result=data.get("final_result"),
            proposal_result_at=data.get("proposal_result_at"),
            counterpart_result_at=data.get("counterpart_result_at"),
            final_result_at=data.get("final_result_at"),
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return mh


@router.patch("/by-pair", response_model=HistoryOut)
def patch_by_pair(payload: HistoryUpdateByPair, db: Session = Depends(get_db)):
    """(to_user_id, target_user_id) 쌍에 대해 최신 히스토리 레코드를 업데이트합니다.

    구현 메모:
        HistoryManager.list_by_to_user로 DB 접근을 수행한 뒤 메모리에서
        target_user_id로 필터링하여 최신(가장 큰 id) 레코드를 선택하고 업데이트합니다.
        이 방식은 '모든 DB 접근은 HistoryManager를 통해서만'이라는 설계 원칙을 준수합니다.
    """
    # fetch records for to_user_id and filter by target_user_id
    rows = history_manager.list_by_to_user(db, to_user_id=payload.to_user_id, skip=0, limit=1000)
    # pick the last (most recent by id) matching target_user_id
    candidates = [r for r in rows if r.target_user_id == payload.target_user_id]
    if not candidates:
        raise HTTPException(status_code=404, detail="history for pair not found")
    mh = candidates[-1]
    try:
        updated = history_manager.update_results(
            db,
            mh.id,
            proposal_result=payload.proposal_result,
            counterpart_result=payload.counterpart_result,
            final_result=payload.final_result,
            proposal_result_at=payload.proposal_result_at,
            counterpart_result_at=payload.counterpart_result_at,
            final_result_at=payload.final_result_at,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return updated


@router.delete("/{id}", status_code=204)
def delete_history(id: int, db: Session = Depends(get_db)):
    try:
        history_manager.delete(db, id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    return None
