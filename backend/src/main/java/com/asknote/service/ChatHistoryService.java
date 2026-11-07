package com.asknote.service;

import com.asknote.common.PageResponse;
import com.asknote.common.auth.CurrentMemberProvider;
import com.asknote.common.exception.BusinessException;
import com.asknote.common.exception.ErrorCode;
import com.asknote.dto.chat.ChatHistoryResponse;
import com.asknote.dto.chat.ChatSource;
import com.asknote.entity.ChatHistory;
import com.asknote.entity.Member;
import com.asknote.repository.ChatHistoryRepository;
import java.util.List;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.stereotype.Service;
import tools.jackson.core.type.TypeReference;
import tools.jackson.databind.ObjectMapper;

/**
 * 질문 기록 (목록 조회) — 구현 담당: Backend 2
 * 회원은 JWT(CurrentMemberProvider)로만 얻는다 — 요청 값으로 회원을 받지 않으므로 남의 기록은 조회할 수 없음
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class ChatHistoryService {

    /** 한 번에 너무 많은 기록을 읽지 않도록 size 상한 (기본 10, API 설계서 1장) */
    static final int MAX_PAGE_SIZE = 50;

    /** 최신순, 같은 초에 저장된 기록은 id 큰 순 (페이지 경계에서 순서가 섞이지 않도록) */
    private static final Sort LATEST_FIRST = Sort.by(Sort.Order.desc("createdAt"), Sort.Order.desc("id"));
    private static final TypeReference<List<ChatSource>> SOURCES_TYPE = new TypeReference<>() {
    };

    private final ChatHistoryRepository chatHistoryRepository;
    private final CurrentMemberProvider currentMemberProvider;
    private final ObjectMapper objectMapper;

    /** 내 질문 기록 목록 (페이지 번호는 0부터) — page < 0, size 가 1~50 밖이면 400 INVALID_INPUT */
    public PageResponse<ChatHistoryResponse> getMyChats(int page, int size) {
        if (page < 0 || size < 1 || size > MAX_PAGE_SIZE) {
            throw new BusinessException(ErrorCode.INVALID_INPUT);
        }
        Member member = currentMemberProvider.getCurrentMember();
        Pageable pageable = PageRequest.of(page, size, LATEST_FIRST);

        return PageResponse.from(chatHistoryRepository.findByMemberId(member.getId(), pageable)
                .map(chat -> ChatHistoryResponse.of(chat, parseSources(chat))));
    }

    /** DB 의 출처 JSON 문자열 → 배열. 없거나 깨진 값이면 빈 배열 (목록 전체가 실패하지 않도록) */
    private List<ChatSource> parseSources(ChatHistory chat) {
        String json = chat.getSources();
        if (json == null || json.isBlank()) {
            return List.of();
        }
        try {
            List<ChatSource> sources = objectMapper.readValue(json, SOURCES_TYPE);
            return sources == null ? List.of() : sources;
        } catch (RuntimeException e) {
            log.warn("출처 JSON 해석 실패 chatId={}", chat.getId());
            return List.of();
        }
    }
}
