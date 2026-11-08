package com.asknote.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.contains;
import static org.mockito.ArgumentMatchers.eq;
import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.verifyNoInteractions;

import com.asknote.common.PageResponse;
import com.asknote.common.audit.AuditLogger;
import com.asknote.common.auth.CurrentMemberProvider;
import com.asknote.common.exception.BusinessException;
import com.asknote.common.exception.ErrorCode;
import com.asknote.dto.chat.ChatFeedbackResponse;
import com.asknote.dto.chat.ChatHistoryResponse;
import com.asknote.dto.chat.ChatSource;
import com.asknote.entity.ChatHistory;
import com.asknote.entity.Feedback;
import com.asknote.entity.Member;
import com.asknote.repository.ChatHistoryRepository;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.mockito.ArgumentCaptor;
import org.springframework.data.domain.PageImpl;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Pageable;
import org.springframework.data.domain.Sort;
import org.springframework.test.util.ReflectionTestUtils;
import tools.jackson.databind.json.JsonMapper;

class ChatHistoryServiceTest {

    private ChatHistoryRepository chatHistoryRepository;
    private CurrentMemberProvider currentMemberProvider;
    private AuditLogger auditLogger;
    private ChatHistoryService chatHistoryService;

    @BeforeEach
    void setUp() {
        chatHistoryRepository = mock(ChatHistoryRepository.class);
        currentMemberProvider = mock(CurrentMemberProvider.class);
        auditLogger = mock(AuditLogger.class);
        chatHistoryService = new ChatHistoryService(chatHistoryRepository, currentMemberProvider,
                JsonMapper.builder().build(), auditLogger);

        Member me = mock(Member.class);
        given(me.getId()).willReturn(7L);
        given(currentMemberProvider.getCurrentMember()).willReturn(me);
    }

    // mock 은 given(...) 밖에서 먼저 만든다 (stub 안에서 다른 mock 을 stub 하면 UnfinishedStubbing)
    private static ChatHistory chat(long id, String sourcesJson, Feedback feedback, LocalDateTime createdAt) {
        ChatHistory c = mock(ChatHistory.class);
        given(c.getId()).willReturn(id);
        given(c.getQuestion()).willReturn("질문 " + id);
        given(c.getAnswer()).willReturn("답변 " + id);
        given(c.getSources()).willReturn(sourcesJson);
        given(c.getFeedback()).willReturn(feedback);
        given(c.getCreatedAt()).willReturn(createdAt);
        return c;
    }

    @Test
    void 내_기록을_최신순_페이지로_조회하고_출처는_배열로_변환() {
        ChatHistory newer = chat(31,
                "[{\"documentId\":1,\"documentName\":\"LangChain_RAG_실습.pdf\",\"page\":12},"
                        + "{\"documentId\":1,\"documentName\":\"LangChain_RAG_실습.pdf\",\"page\":14}]",
                Feedback.HELPFUL, LocalDateTime.of(2026, 11, 9, 14, 32, 0, 500_000_000));
        ChatHistory older = chat(30, "[{\"documentId\":2,\"documentName\":\"Spring_Security_JWT.pdf\",\"page\":31}]",
                null, LocalDateTime.of(2026, 11, 9, 11, 25));
        given(chatHistoryRepository.findByMemberId(eq(7L), any(Pageable.class)))
                .willReturn(new PageImpl<>(List.of(newer, older), PageRequest.of(0, 2), 13));

        PageResponse<ChatHistoryResponse> result = chatHistoryService.getMyChats(0, 2);

        // 로그인 회원 id 로만 조회, 페이지 · 정렬(createdAt desc → id desc) 확인
        ArgumentCaptor<Pageable> captor = ArgumentCaptor.forClass(Pageable.class);
        verify(chatHistoryRepository).findByMemberId(eq(7L), captor.capture());
        assertThat(captor.getValue().getPageNumber()).isZero();
        assertThat(captor.getValue().getPageSize()).isEqualTo(2);
        assertThat(captor.getValue().getSort())
                .isEqualTo(Sort.by(Sort.Order.desc("createdAt"), Sort.Order.desc("id")));

        // 페이지 응답 형식 (mock-data chats/list.200-page0.json)
        assertThat(result.page()).isZero();
        assertThat(result.size()).isEqualTo(2);
        assertThat(result.totalElements()).isEqualTo(13);
        assertThat(result.totalPages()).isEqualTo(7);
        assertThat(result.content()).extracting(ChatHistoryResponse::id).containsExactly(31L, 30L);

        ChatHistoryResponse first = result.content().get(0);
        assertThat(first.sources()).containsExactly(
                new ChatSource(1L, "LangChain_RAG_실습.pdf", 12),
                new ChatSource(1L, "LangChain_RAG_실습.pdf", 14));
        assertThat(first.feedback()).isEqualTo("HELPFUL");
        assertThat(first.createdAt()).isEqualTo(LocalDateTime.of(2026, 11, 9, 14, 32, 0));
        assertThat(result.content().get(1).feedback()).isNull();
    }

    @Test
    void 출처가_없거나_깨진_JSON_이면_빈_배열() {
        ChatHistory noSources = chat(2, null, null, LocalDateTime.of(2026, 11, 9, 10, 0));
        ChatHistory broken = chat(1, "not-json", null, LocalDateTime.of(2026, 11, 9, 9, 0));
        given(chatHistoryRepository.findByMemberId(eq(7L), any(Pageable.class)))
                .willReturn(new PageImpl<>(List.of(noSources, broken), PageRequest.of(0, 10), 2));

        PageResponse<ChatHistoryResponse> result = chatHistoryService.getMyChats(0, 10);

        assertThat(result.content()).allSatisfy(c -> assertThat(c.sources()).isEmpty());
    }

    @Test
    void 기록이_없으면_빈_페이지() {
        given(chatHistoryRepository.findByMemberId(eq(7L), any(Pageable.class)))
                .willReturn(new PageImpl<>(List.of(), PageRequest.of(0, 10), 0));

        PageResponse<ChatHistoryResponse> result = chatHistoryService.getMyChats(0, 10);

        assertThat(result.content()).isEmpty();
        assertThat(result.totalElements()).isZero();
        assertThat(result.totalPages()).isZero();
    }

    @Test
    void 잘못된_page_size_는_INVALID_INPUT() {
        for (int[] ps : new int[][] {{-1, 10}, {0, 0}, {0, ChatHistoryService.MAX_PAGE_SIZE + 1}}) {
            assertThatThrownBy(() -> chatHistoryService.getMyChats(ps[0], ps[1]))
                    .isInstanceOf(BusinessException.class)
                    .extracting(e -> ((BusinessException) e).getErrorCode())
                    .isEqualTo(ErrorCode.INVALID_INPUT);
        }
        verify(chatHistoryRepository, never()).findByMemberId(any(), any());
    }

    // ---- 답변 피드백 (PATCH /api/chats/{id}/feedback) ----
    // 소유자 비교(isOwnedBy)가 실제로 동작해야 하므로 mock 이 아닌 실제 엔티티에 id 만 넣어 사용

    private static Member realMember(long id, String email) {
        Member m = Member.createMember(email, "encoded");
        ReflectionTestUtils.setField(m, "id", id);
        return m;
    }

    private static ChatHistory realChat(long id, Member owner) {
        ChatHistory c = new ChatHistory(owner, "질문", "답변", "[]");
        ReflectionTestUtils.setField(c, "id", id);
        return c;
    }

    @Test
    void 내_기록에_피드백_등록_변경_같은값_재요청() {
        Member student = realMember(7L, "student@test.com");
        ChatHistory chat = realChat(31L, student);
        given(currentMemberProvider.getCurrentMember()).willReturn(student);
        given(chatHistoryRepository.findWithMemberById(31L)).willReturn(Optional.of(chat));

        ChatFeedbackResponse helpful = chatHistoryService.updateFeedback(31L, Feedback.HELPFUL);
        assertThat(helpful).isEqualTo(new ChatFeedbackResponse(31L, "HELPFUL"));
        assertThat(chat.getFeedback()).isEqualTo(Feedback.HELPFUL);

        assertThat(chatHistoryService.updateFeedback(31L, Feedback.NOT_HELPFUL).feedback()).isEqualTo("NOT_HELPFUL");
        // 같은 값을 다시 보내도 결과가 같음 (PATCH 멱등)
        assertThat(chatHistoryService.updateFeedback(31L, Feedback.NOT_HELPFUL).feedback()).isEqualTo("NOT_HELPFUL");
        verifyNoInteractions(auditLogger);
    }

    @Test
    void 없는_기록은_CHAT_NOT_FOUND() {
        given(currentMemberProvider.getCurrentMember()).willReturn(realMember(7L, "student@test.com"));
        given(chatHistoryRepository.findWithMemberById(999L)).willReturn(Optional.empty());

        assertThatThrownBy(() -> chatHistoryService.updateFeedback(999L, Feedback.HELPFUL))
                .isInstanceOf(BusinessException.class)
                .extracting(e -> ((BusinessException) e).getErrorCode())
                .isEqualTo(ErrorCode.CHAT_NOT_FOUND);
    }

    @Test
    void 남의_기록은_FORBIDDEN_값은_그대로_감사로그_기록() {
        Member student = realMember(7L, "student@test.com");
        Member other = realMember(8L, "other@test.com");
        ChatHistory othersChat = realChat(13L, other);
        given(currentMemberProvider.getCurrentMember()).willReturn(student);
        given(chatHistoryRepository.findWithMemberById(13L)).willReturn(Optional.of(othersChat));

        assertThatThrownBy(() -> chatHistoryService.updateFeedback(13L, Feedback.NOT_HELPFUL))
                .isInstanceOf(BusinessException.class)
                .extracting(e -> ((BusinessException) e).getErrorCode())
                .isEqualTo(ErrorCode.FORBIDDEN);
        assertThat(othersChat.getFeedback()).isNull();
        verify(auditLogger).ownershipDenied(eq("student@test.com"), contains("/api/chats/13/feedback"));
    }
}
