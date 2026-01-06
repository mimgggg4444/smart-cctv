import cv2
import requests
from requests.auth import HTTPBasicAuth
import numpy as np
from ultralytics import YOLO
import time
from datetime import datetime

# IP Webcam 설정
USERNAME = "testwebcam"
PASSWORD = "1234"
SNAPSHOT_URL = "http://192.168.0.36:8080/shot.jpg"

# Node.js API 주소
API_URL = "http://localhost:8000/api/events"

print("🤖 YOLO 모델 로딩...")
model = YOLO('yolov8n.pt')

print("📸 AI 감지 + DB 저장 시작...\n")

frame_count = 0
last_save_time = 0
SAVE_COOLDOWN = 5  # 5초마다 한 번만 저장

while True:
    try:
        # 이미지 가져오기
        response = requests.get(
            SNAPSHOT_URL, 
            auth=HTTPBasicAuth(USERNAME, PASSWORD),
            timeout=5
        )
        
        if response.status_code != 200:
            print(f"❌ HTTP 에러: {response.status_code}")
            time.sleep(1)
            continue
        
        img_array = np.array(bytearray(response.content), dtype=np.uint8)
        frame = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
        
        if frame is None:
            time.sleep(0.5)
            continue
        
        frame_count += 1
        
        # AI 분석
        results = model(frame, verbose=False)
        detections = results[0].boxes
        
        # 바닥 물체 감지
        height = frame.shape[0]
        floor_objects = []
        
        for box in detections:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            cls = int(box.cls[0])
            conf = float(box.conf[0])
            
            if y2 > height * 0.5:
                class_name = model.names[cls]
                floor_objects.append({
                    'name': class_name,
                    'confidence': conf,
                    'position': [int(x1), int(y1), int(x2), int(y2)]
                })
        
        current_time = time.time()
        
        # 물체 감지되고 쿨다운 지났으면 DB 저장
        if floor_objects and (current_time - last_save_time) > SAVE_COOLDOWN:
            print(f"🔍 [{frame_count}] 바닥 물체 감지:")
            for obj in floor_objects:
                print(f"   - {obj['name']}: {obj['confidence']:.2%}")
            
            # Node.js API로 전송
            try:
                api_response = requests.post(API_URL, json={
                    'type': 'floor_object_detected',
                    'timestamp': datetime.now().isoformat(),
                    'object_count': len(floor_objects),
                    'confidence': max([obj['confidence'] for obj in floor_objects]),
                    'metadata': {
                        'objects': floor_objects,
                        'frame_number': frame_count
                    }
                }, timeout=3)
                
                if api_response.status_code == 200:
                    print("💾 DB 저장 완료\n")
                    last_save_time = current_time
                else:
                    print(f"❌ API 오류: {api_response.status_code}\n")
                    
            except Exception as e:
                print(f"❌ API 연결 실패: {e}\n")
        
        # 화면 표시
        annotated_frame = results[0].plot()
        cv2.line(annotated_frame, (0, height//2), (frame.shape[1], height//2), (0, 255, 0), 2)
        cv2.imshow('AI Detection', annotated_frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
        
        time.sleep(0.1)
        
    except KeyboardInterrupt:
        print("\n👋 종료")
        break
    except Exception as e:
        print(f"❌ 에러: {e}")
        time.sleep(1)

cv2.destroyAllWindows()