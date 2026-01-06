from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, JSON
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime
from pydantic import BaseModel
from typing import Optional, Dict

# DB 설정
DATABASE_URL = "postgresql://postgres:1234@localhost:5432/smarthome"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(bind=engine)
Base = declarative_base()

# ===== 모델 =====
class DetectionEvent(Base):
    __tablename__ = "detection_events"
    
    id = Column(Integer, primary_key=True, index=True)
    type = Column(String)
    timestamp = Column(DateTime)
    object_count = Column(Integer, nullable=True)
    confidence = Column(Float, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

class ActivityLog(Base):
    __tablename__ = "activity_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    activity = Column(String)
    zone = Column(String, nullable=True)
    timestamp = Column(DateTime)
    duration = Column(Integer, nullable=True)  # 초 단위
    confidence = Column(Float, nullable=True)
    details = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

# 테이블 생성
Base.metadata.create_all(bind=engine)

# ===== FastAPI 앱 =====
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ===== Request 모델 =====
class EventCreate(BaseModel):
    type: str
    timestamp: str
    object_count: Optional[int] = None
    confidence: Optional[float] = None
    metadata: Optional[Dict] = None

class ActivityCreate(BaseModel):
    activity: str
    zone: Optional[str] = None
    timestamp: str
    duration: Optional[int] = None
    confidence: Optional[float] = None
    details: Optional[Dict] = None

# ===== 감지 이벤트 API =====
@app.post("/api/events")
async def create_event(event: EventCreate):
    db = SessionLocal()
    
    try:
        db_event = DetectionEvent(
            type=event.type,
            timestamp=datetime.fromisoformat(event.timestamp),
            object_count=event.object_count,
            confidence=event.confidence,
            details=event.metadata
        )
        
        db.add(db_event)
        db.commit()
        db.refresh(db_event)
        
        print(f"✅ [Event {db_event.id}] {event.type} 저장")
        result = {"success": True, "id": db_event.id}
        
    except Exception as e:
        db.rollback()
        print(f"❌ Event 저장 실패: {e}")
        result = {"success": False, "error": str(e)}
    
    finally:
        db.close()
    
    return result

@app.get("/api/events")
async def get_events(limit: int = 50):
    db = SessionLocal()
    events = db.query(DetectionEvent).order_by(
        DetectionEvent.timestamp.desc()
    ).limit(limit).all()
    db.close()
    
    return [
        {
            "id": e.id,
            "type": e.type,
            "timestamp": e.timestamp.isoformat(),
            "object_count": e.object_count,
            "confidence": e.confidence,
            "details": e.details
        }
        for e in events
    ]

# ===== 활동 로그 API =====
@app.post("/api/activities")
async def create_activity(activity: ActivityCreate):
    db = SessionLocal()
    
    try:
        db_activity = ActivityLog(
            activity=activity.activity,
            zone=activity.zone,
            timestamp=datetime.fromisoformat(activity.timestamp),
            duration=activity.duration,
            confidence=activity.confidence,
            details=activity.details
        )
        
        db.add(db_activity)
        db.commit()
        db.refresh(db_activity)
        
        print(f"✅ [Activity {db_activity.id}] {activity.activity} ({activity.duration}초)")
        result = {"success": True, "id": db_activity.id}
        
    except Exception as e:
        db.rollback()
        print(f"❌ Activity 저장 실패: {e}")
        result = {"success": False, "error": str(e)}
    
    finally:
        db.close()
    
    return result

@app.get("/api/activities")
async def get_activities(limit: int = 100, date: Optional[str] = None):
    db = SessionLocal()
    
    query = db.query(ActivityLog).order_by(ActivityLog.timestamp.desc())
    
    # 특정 날짜 필터
    if date:
        target_date = datetime.fromisoformat(date)
        query = query.filter(
            ActivityLog.timestamp >= target_date.replace(hour=0, minute=0, second=0),
            ActivityLog.timestamp < target_date.replace(hour=23, minute=59, second=59)
        )
    
    activities = query.limit(limit).all()
    db.close()
    
    return [
        {
            "id": a.id,
            "activity": a.activity,
            "zone": a.zone,
            "timestamp": a.timestamp.isoformat(),
            "duration": a.duration,
            "confidence": a.confidence,
            "details": a.details
        }
        for a in activities
    ]

# ===== 통계 API (범용) =====
@app.get("/api/stats")
async def get_stats():
    db = SessionLocal()
    
    today = datetime.now().replace(hour=0, minute=0, second=0)
    
    # 감지 이벤트 통계
    today_events = db.query(DetectionEvent).filter(
        DetectionEvent.timestamp >= today
    ).count()
    total_events = db.query(DetectionEvent).count()
    
    # 활동 통계
    today_activities = db.query(ActivityLog).filter(
        ActivityLog.timestamp >= today
    ).count()
    total_activities = db.query(ActivityLog).count()
    
    db.close()
    
    return {
        "events": {
            "today": today_events,
            "total": total_events
        },
        "activities": {
            "today": today_activities,
            "total": total_activities
        }
    }

# ===== 활동 요약 API =====
@app.get("/api/activities/summary")
async def get_activity_summary(date: Optional[str] = None):
    db = SessionLocal()
    
    # 날짜 필터
    if date:
        target_date = datetime.fromisoformat(date)
    else:
        target_date = datetime.now()
    
    start = target_date.replace(hour=0, minute=0, second=0)
    end = target_date.replace(hour=23, minute=59, second=59)
    
    activities = db.query(ActivityLog).filter(
        ActivityLog.timestamp >= start,
        ActivityLog.timestamp <= end
    ).all()
    
    db.close()
    
    # 활동별 총 시간 계산
    summary = {}
    for act in activities:
        activity_name = act.activity
        duration = act.duration or 0
        
        if activity_name not in summary:
            summary[activity_name] = {
                'total_seconds': 0,
                'count': 0
            }
        
        summary[activity_name]['total_seconds'] += duration
        summary[activity_name]['count'] += 1
    
    # 시간 포맷 변환
    result = {}
    for activity, data in summary.items():
        total_seconds = data['total_seconds']
        hours = total_seconds // 3600
        minutes = (total_seconds % 3600) // 60
        
        result[activity] = {
            'total_time': f"{hours}시간 {minutes}분",
            'total_seconds': total_seconds,
            'count': data['count']
        }
    
    return {
        "date": target_date.strftime("%Y-%m-%d"),
        "summary": result
    }

if __name__ == "__main__":
    import uvicorn
    print("🚀 서버 시작: http://localhost:8000")
    print("📊 API 문서: http://localhost:8000/docs")
    print("📋 엔드포인트:")
    print("  - POST /api/events (감지 이벤트)")
    print("  - GET  /api/events")
    print("  - POST /api/activities (활동 로그)")
    print("  - GET  /api/activities")
    print("  - GET  /api/activities/summary (일일 요약)")
    print("  - GET  /api/stats (전체 통계)")
    uvicorn.run(app, host="0.0.0.0", port=8000)