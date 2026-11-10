# AskNote — Kubernetes(Minikube) 배포

`docker-compose.prod.yml` 구성을 Kubernetes 리소스로 옮긴 것입니다. 운영 EC2(Compose)와 **별개로 로컬 Minikube 에서만** 실행합니다.
이미지는 새로 빌드하지 않고 Docker Hub 이미지 `sha-7d08b42`(11/10 테스트 당시 운영 이미지)를 그대로 씁니다.

## 구성

| 파일 | 리소스 | Compose 대응 |
|------|--------|--------------|
| `namespace.yaml` | Namespace `asknote` | - |
| `configmap.yaml` | ConfigMap `asknote-config` (비밀이 아닌 설정) | `environment:` 일반 값 |
| `secret.example.yaml` | Secret `asknote-secret` **키 이름만** (값 없음, 적용 안 함) | `.env` 비밀 값 |
| `database.yaml` | PVC `db-data` + Deployment + Service(ClusterIP) | `database` · `db-data` |
| `ai-service.yaml` | PVC `chroma-data` + Deployment + Service(ClusterIP) | `ai-service` · `chroma-data` |
| `backend.yaml` | Deployment(+ 의존 서비스 대기 initContainer) + Service(ClusterIP) | `backend` · `depends_on` |
| `frontend.yaml` | Deployment + Service(**NodePort 30080**) | `frontend` · `80:8080` |
| `networkpolicy.yaml` | NetworkPolicy 5개 | `edge-net` · `ai-net` · `db-net(internal)` |
| `kustomization.yaml` | 위 리소스 묶음 + 이미지 태그 | `IMAGE_TAG` |

- Service 이름을 Compose 서비스 이름과 같게(`database` · `ai-service` · `backend`) 두어 `nginx.conf` · `DB_HOST` · `AI_SERVICE_URL` 수정 없이 동작합니다.
- Compose 와 같은 보안 설정: `allowPrivilegeEscalation: false`(no-new-privileges), database 외 `capabilities.drop: [ALL]`, `resources.limits.memory`(mem_limit), 서비스별 필요한 환경 변수만 전달(`valueFrom` 키 단위).
- 외부 노출은 frontend 하나뿐이고, backend · ai-service · database 는 ClusterIP(클러스터 내부 전용)입니다.

## 실행 (Windows Git Bash 기준)

### 1. 클러스터 시작 (전용 프로필, Calico CNI)

```bash
minikube start -p asknote --driver=docker --cni=calico --memory=4096 --cpus=2
kubectl config current-context        # asknote
```

- `-p asknote`: 기존 Minikube 클러스터와 분리된 전용 프로필 (기존 클러스터를 지우지 않음)
- `--cni=calico`: NetworkPolicy 를 실제로 적용하려면 필요 (기본 CNI 는 정책을 무시)
- 메모리 4GB: 4개 Pod 의 메모리 상한 합계 약 2.6GiB + 시스템 Pod 여유

### 2. Secret 생성 (값은 저장소 밖 파일에서)

저장소 **밖**에 `k8s-secret.env` 를 만들고 아래 8개 키를 채웁니다 (예: `C:\rookies6\secure\k8s-secret.env`).

```env
MARIADB_ROOT_PASSWORD=
MARIADB_PASSWORD=
JWT_SECRET=
AI_INTERNAL_TOKEN=
ADMIN_EMAIL=
ADMIN_PASSWORD=
OPENAI_API_KEY=
GROQ_API_KEY=
```

- 값 생성: `openssl rand -hex 32`(JWT_SECRET · AI_INTERNAL_TOKEN), `openssl rand -hex 24`(DB 비밀번호), `echo 'Adm!n1'"$(openssl rand -hex 6)"`(ADMIN_PASSWORD 규칙: 8~20자 · 영문 · 숫자 · 특수문자)
- 따옴표 없이 `KEY=값` 형식, 줄바꿈은 LF (`sed -i 's/\r$//' 파일`)

```bash
cd /c/rookies6/mini_project_3
kubectl apply -f k8s/namespace.yaml
kubectl -n asknote create secret generic asknote-secret --from-env-file=C:/rookies6/secure/k8s-secret.env
kubectl -n asknote describe secret asknote-secret   # 키 이름 · 바이트 수만 표시 (값 미표시)
```

- `minikube stop` 후 다시 `start` 한 경우 Secret 은 남아 있으므로 이 단계는 건너뜁니다 (`already exists` 오류는 정상).
- 값을 바꿀 때: `kubectl -n asknote delete secret asknote-secret` 후 다시 생성 → `kubectl -n asknote rollout restart deploy`

### 3. 배포

```bash
kubectl apply -k k8s/
kubectl -n asknote get pods -w        # 4개 모두 READY 1/1 · Running 이 되면 Ctrl+C
```

첫 실행은 이미지 다운로드 때문에 몇 분 걸립니다. backend 는 initContainer 가 database · ai-service 준비를 기다린 뒤 시작합니다.

### 4. 접속

```bash
kubectl -n asknote port-forward svc/frontend 8080:80
```

브라우저에서 `http://localhost:8080` → 회원가입 → PDF 업로드 → 질문.
(접속 주소를 바꾸면 `configmap.yaml` 의 `CORS_ALLOWED_ORIGINS` 도 같이 바꾸고 `kubectl apply -k k8s/` → `kubectl -n asknote rollout restart deploy/backend`)

## 확인 (발표 · 문서 근거)

```bash
kubectl -n asknote get all                                  # Deployment · Pod · Service
kubectl -n asknote get configmap,secret,pvc,networkpolicy   # 설정 · 비밀 분리, 볼륨, 네트워크 정책

# 비root 실행
kubectl -n asknote exec deploy/backend -- id
kubectl -n asknote exec deploy/ai-service -- id

# NetworkPolicy — frontend 에서 AI · DB 직접 접근 차단 (시간 초과가 정상)
kubectl -n asknote exec deploy/frontend -- wget -q -T 3 -O- http://ai-service:8000/health || echo "차단됨"
kubectl -n asknote exec deploy/frontend -- nc -z -w 3 database 3306 || echo "차단됨"
# backend 에서는 AI 접근 가능 (정상 응답)
kubectl -n asknote exec deploy/backend -- curl -fsS http://ai-service:8000/health
```

- Secret 값을 출력하는 명령(`get secret -o yaml`, `-o jsonpath`, 컨테이너 안 `env`)은 실행 · 캡처하지 않습니다.
- 캡처 추천: `get all` · `get configmap,secret,pvc,networkpolicy` · `describe secret`(바이트 수만) · `id` · NetworkPolicy 차단/허용 결과 · 브라우저(`localhost:8080`) 질문 화면

## 정리

```bash
minikube stop -p asknote      # 중지 (데이터 유지)
minikube delete -p asknote    # 이 프로필만 삭제 (다른 Minikube 클러스터 영향 없음)
```

## 문제 해결

| 증상 | 원인 · 조치 |
|------|-------------|
| backend 가 `Init:0/1` 에서 멈춤 | database · ai-service 가 아직 준비 전 → `kubectl -n asknote logs deploy/backend -c wait-dependencies` |
| `CreateContainerConfigError` | Secret 이 없거나 키 이름 오타 → 2단계 확인 (`describe secret` 의 키 목록) |
| ai-service 업로드 시 권한 오류 | 볼륨 쓰기 권한 → `kubectl -n asknote exec deploy/ai-service -- id` 로 gid 확인 후 `securityContext.fsGroup` 지정 |
| 로그인 시 403 | `CORS_ALLOWED_ORIGINS` 와 접속 주소 불일치 → 4단계 참고 |
| 관리자 계정이 안 만들어짐 | `ADMIN_PASSWORD` 규칙 위반 → `kubectl -n asknote logs deploy/backend \| grep -i 관리자` |
| Pod 가 `OOMKilled` · `Pending` | Minikube 메모리 부족 → `--memory=4096` 이상으로 다시 시작 |
