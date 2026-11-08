# =========================================================
#  Backend (Spring Boot 4.0.x · Java 17) - 멀티스테이지 · 비root · HEALTHCHECK
#  빌드: eclipse-temurin:17.0.21_9-jdk-resolute + Maven Wrapper  →  실행: eclipse-temurin:17.0.21_9-jre-resolute
# =========================================================

# ---------- 1) 빌드 단계: JDK + Maven Wrapper ----------
# 베이스 이미지는 패치 버전 태그 + digest 로 고정 (보안점검서 I-4). 갱신 시 태그 · digest 를 함께 바꾸고 Trivy 재검사
FROM eclipse-temurin:17.0.21_9-jdk-resolute@sha256:b5e475b49399b918176adc274c95e02db1057f8d6dbc891dad17d29d811c5a5c AS build
WORKDIR /workspace

# 의존성 먼저 받기 → pom.xml 이 안 바뀌면 이 레이어는 캐시 재사용
COPY .mvn/ .mvn/
COPY mvnw pom.xml ./
RUN chmod +x mvnw && ./mvnw -B -q dependency:go-offline

# 소스 복사 후 패키징 (테스트는 DB 가 필요하므로 이미지 빌드에서는 생략)
COPY src/ src/
RUN ./mvnw -B -q package -DskipTests && cp target/*.jar app.jar

# ---------- 2) 실행 단계: JRE 만 ----------
FROM eclipse-temurin:17.0.21_9-jre-resolute@sha256:d532593b4d17f9455bcc74b4b45046fd0f9799db3b50b3486091e3e33ad99a26

# 비root 전용 사용자 (로그인 셸 없음) - 보안점검서 I-2
RUN groupadd --system app && useradd --system --gid app --no-create-home --shell /usr/sbin/nologin app

WORKDIR /app
# jar 는 root 소유 그대로 둠 → app 사용자는 읽기만 가능, 수정 불가
COPY --from=build /workspace/app.jar app.jar

USER app
EXPOSE 8080

# /actuator/health 는 permitAll (UP/DOWN 만). Compose healthcheck 와 같은 값
HEALTHCHECK --interval=15s --timeout=5s --start-period=40s --retries=5 \
  CMD curl -fsS http://127.0.0.1:8080/actuator/health || exit 1

ENTRYPOINT ["java", "-XX:MaxRAMPercentage=75", "-jar", "app.jar"]
