package com.asknote.config;

import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.reactive.function.client.WebClient;

/**
 * AI Module 내부 호출용 WebClient — 모든 요청에 X-Internal-Token
 * 주소 · 토큰은 환경 변수 AI_SERVICE_URL · AI_INTERNAL_TOKEN (코드에 쓰지 않음)
 */
@Slf4j
@Configuration
public class AiClientConfig {

    public static final String INTERNAL_TOKEN_HEADER = "X-Internal-Token";

    @Bean
    public WebClient aiWebClient(@Value("${ai.service-url}") String serviceUrl,
                                 @Value("${ai.internal-token}") String internalToken) {
        if (internalToken.isBlank()) {
            log.warn("AI_INTERNAL_TOKEN 이 비어 있습니다 — AI Module 호출이 401 로 거부됩니다");
        }
        // Boot 4 는 WebClient.Builder 자동 설정이 별도 모듈이라 직접 생성
        return WebClient.builder()
                .baseUrl(serviceUrl)
                .defaultHeader(INTERNAL_TOKEN_HEADER, internalToken)
                .build();
    }
}
