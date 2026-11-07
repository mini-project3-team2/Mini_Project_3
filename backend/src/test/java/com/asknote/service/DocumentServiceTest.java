package com.asknote.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.verify;

import com.asknote.client.AiDocumentClient;
import com.asknote.common.audit.AuditLogger;
import com.asknote.common.auth.CurrentMemberProvider;
import com.asknote.dto.document.DocumentResponse;
import com.asknote.entity.Document;
import com.asknote.entity.DocumentStatus;
import com.asknote.entity.Member;
import com.asknote.repository.DocumentRepository;
import java.time.LocalDateTime;
import java.util.List;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

class DocumentServiceTest {

    private DocumentRepository documentRepository;
    private CurrentMemberProvider currentMemberProvider;
    private DocumentService documentService;

    @BeforeEach
    void setUp() {
        documentRepository = mock(DocumentRepository.class);
        currentMemberProvider = mock(CurrentMemberProvider.class);
        documentService = new DocumentService(documentRepository, currentMemberProvider,
                mock(PdfValidator.class), mock(AiDocumentClient.class), mock(AuditLogger.class));

        Member me = mock(Member.class);
        given(me.getId()).willReturn(7L);
        given(currentMemberProvider.getCurrentMember()).willReturn(me);
    }

    private static Document document(long id, String name, DocumentStatus status, LocalDateTime createdAt) {
        Document d = mock(Document.class);
        given(d.getId()).willReturn(id);
        given(d.getOriginalFilename()).willReturn(name);
        given(d.getFileSize()).willReturn(1000L);
        given(d.getStatus()).willReturn(status);
        given(d.getCreatedAt()).willReturn(createdAt);
        return d;
    }

    @Test
    void 내_자료_목록은_로그인_회원_id_로만_조회하고_최신순을_유지() {
        // mock 자료는 given(...) 밖에서 먼저 만든다 (stub 안에서 다른 mock 을 stub 하면 UnfinishedStubbing)
        Document newer = document(3, "Docker_Compose_정리.pdf", DocumentStatus.INDEXING,
                LocalDateTime.of(2026, 11, 9, 9, 58, 0, 123_000_000));
        Document older = document(2, "Spring_Security_JWT.pdf", DocumentStatus.READY,
                LocalDateTime.of(2026, 11, 7, 11, 20));
        given(documentRepository.findByMemberIdOrderByCreatedAtDescIdDesc(7L)).willReturn(List.of(newer, older));

        List<DocumentResponse> result = documentService.getMyDocuments();

        verify(documentRepository).findByMemberIdOrderByCreatedAtDescIdDesc(7L);
        assertThat(result).extracting(DocumentResponse::id).containsExactly(3L, 2L);
        assertThat(result).extracting(DocumentResponse::status).containsExactly("INDEXING", "READY");
        // 응답 시간은 초 단위 (mock-data 형식 "2026-11-09T09:58:00")
        assertThat(result.get(0).createdAt()).isEqualTo(LocalDateTime.of(2026, 11, 9, 9, 58, 0));
    }

    @Test
    void 자료가_없으면_빈_배열() {
        given(documentRepository.findByMemberIdOrderByCreatedAtDescIdDesc(7L)).willReturn(List.of());

        assertThat(documentService.getMyDocuments()).isEmpty();
    }
}
