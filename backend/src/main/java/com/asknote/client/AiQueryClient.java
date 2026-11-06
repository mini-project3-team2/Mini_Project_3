package com.asknote.client;

import com.asknote.dto.ai.QueryRequest;
import java.time.Duration;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.core.ParameterizedTypeReference;
import org.springframework.http.MediaType;
import org.springframework.http.codec.ServerSentEvent;
import org.springframework.stereotype.Component;
import org.springframework.web.reactive.function.client.WebClient;
import reactor.core.publisher.Flux;

/**
 * AI Module 질의 스트리밍 (API 설계서 6.3) — SSE 이벤트를 그대로 받아 Flux 로 넘긴다
 * 타임아웃: 이벤트 사이 간격이 stream-seconds 를 넘으면 TimeoutException
 */
@Component
public class AiQueryClient {

    private static final ParameterizedTypeReference<ServerSentEvent<String>> SSE_TYPE =
            new ParameterizedTypeReference<>() {
            };

    private final WebClient aiWebClient;
    private final Duration streamTimeout;

    public AiQueryClient(WebClient aiWebClient,
                         @Value("${ai.timeout.stream-seconds}") long streamSeconds) {
        this.aiWebClient = aiWebClient;
        this.streamTimeout = Duration.ofSeconds(streamSeconds);
    }

    public Flux<ServerSentEvent<String>> stream(QueryRequest request) {
        return aiWebClient.post()
                .uri("/internal/query/stream")
                .contentType(MediaType.APPLICATION_JSON)
                .accept(MediaType.TEXT_EVENT_STREAM)
                .bodyValue(request)
                .retrieve()
                .bodyToFlux(SSE_TYPE)
                .timeout(streamTimeout);
    }

    public Duration getStreamTimeout() {
        return streamTimeout;
    }
}
