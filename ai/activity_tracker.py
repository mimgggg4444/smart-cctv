# activity_tracker.py
import cv2
import requests
from requests.auth import HTTPBasicAuth
import numpy as np
from ultralytics import YOLO
from datetime import datetime
import time

USERNAME = "testwebcam"
PASSWORD = "1234"
SNAPSHOT_URL = "http://192.168.0.36:8080/shot.jpg"
API_URL = "http://localhost:8000/api/activities"

# 방 영역 정의 (실제 방 레이아웃에 맞게 조정)
ZONES = {
    'desk': {'x1': 0, 'y1': 0, 'x2': 960, 'y2': 1080},
    'piano': {'x1': 960, 'y1': 0, 'x2': 1440, 'y2': 1080},
    'bed': {'x1': 1440, 'y1': 0, 'x2': 1920, 'y2': 1080},
}

model = YOLO('yolov8n.pt')

current_activity = None
activity_start = None

def get_person_center(box):
    x1, y1, x2, y2 = box.xyxy[0].tolist()
    return ((x1 + x2) / 2, (y1 + y2) / 2)

def get_zone(x, y):
    for zone_name, coords in ZONES.items():
        if coords['x1'] <= x <= coords['x2'] and coords['y1'] <= y <= coords['y2']:
            return zone_name
    return 'other'

def detect_activity(zone, objects, person_box):
    # 높이로 자세 추정 (간단 버전)
    _, y1, _, y2 = person_box
    height_ratio = (y2 - y1) / 1080
    
    if zone == 'desk':
        if 'laptop' in objects:
            return 'laptop_work'
        elif any(obj in objects for obj in ['keyboard', 'mouse']):
            return 'desktop_work'
        elif height_ratio > 0.5:  # 앉아있음
            return 'sitting_at_desk'
        return 'at_desk'
    
    elif zone == 'piano':
        return 'playing_piano'
    
    elif zone == 'bed':
        if height_ratio > 0.6:  # 누워있음
            return 'lying_on_bed'
        return 'on_bed'
    
    return 'idle'

print("🎯 생활 패턴 트래킹 시작...\n")

while True:
    try:
        response = requests.get(SNAPSHOT_URL, auth=HTTPBasicAuth(USERNAME, PASSWORD), timeout=5)
        img_array = np.array(bytearray(response.content), dtype=np.uint8)
        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        if frame is None:
            continue
        
        results = model(frame, verbose=False)
        detections = results[0].boxes
        
        # 사람 찾기
        person = None
        objects = []
        
        for box in detections:
            cls = int(box.cls[0])
            class_name = model.names[cls]
            
            if class_name == 'person':
                person = box.xyxy[0].tolist()
            else:
                objects.append(class_name)
        
        if person:
            x, y = get_person_center(box)
            zone = get_zone(x, y)
            activity = detect_activity(zone, objects, person)
            
            now = datetime.now()
            
            # 활동 변경 감지
            if activity != current_activity:
                if current_activity:
                    duration = (now - activity_start).seconds
                    print(f"📝 {current_activity} → {duration}초")
                    
                    # DB 저장
                    requests.post(API_URL, json={
                        'activity': current_activity,
                        'zone': zone,
                        'timestamp': activity_start.isoformat(),
                        'duration': duration
                    })
                
                current_activity = activity
                activity_start = now
                print(f"\n🎯 현재 활동: {activity} (위치: {zone})")
        
        # 화면 표시 (영역 구분선)
        annotated = results[0].plot()
        for zone_name, coords in ZONES.items():
            cv2.rectangle(annotated, 
                         (coords['x1'], coords['y1']), 
                         (coords['x2'], coords['y2']), 
                         (0, 255, 0), 2)
            cv2.putText(annotated, zone_name, 
                       (coords['x1']+10, coords['y1']+30),
                       cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2)
        
        cv2.imshow('Activity Tracker', annotated)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        
        time.sleep(0.5)
        
    except KeyboardInterrupt:
        break
    except Exception as e:
        print(f"❌ {e}")
        time.sleep(1)

cv2.destroyAllWindows()
