package com.asknote.service;

import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.ArgumentMatchers.anyLong;
import static org.mockito.ArgumentMatchers.anyString;
import static org.mockito.BDDMockito.given;
import static org.mockito.Mockito.mock;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;

import com.asknote.client.AiDocumentClient;
import com.asknote.common.audit.AuditLogger;
import com.asknote.common.auth.CurrentMemberProvider;
import com.asknote.common.exception.BusinessException;
import com.asknote.common.exception.ErrorCode;
import com.asknote.dto.document.DocumentResponse;
import com.asknote.entity.Document;
import com.asknote.entity.DocumentStatus;
import com.asknote.entity.Member;
import com.asknote.repository.DocumentRepository;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Optional;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.springframework.mock.web.MockMultipartFile;

class DocumentServiceTest {

    private static final String MY_UUID = "8f14e45f-ceea-467f-a0e6-1a2b3c4d5e6f";

    private DocumentRepository documentRepository;
    private CurrentMemberProvider currentMemberProvider;
    private AiDocumentClient aiDocumentClient;
    private Member me;
    private DocumentService documentService;

    @BeforeEach
    void setUp() {
        documentRepository = mock(DocumentRepository.class);
        currentMemberProvider = mock(CurrentMemberProvider.class);
        aiDocumentClient = mock(AiDocumentClient.class);
        documentService = new DocumentService(documentRepository, currentMemberProvider,
                mock(PdfValidator.class), aiDocumentClient, mock(AuditLogger.class));

        me = mock(Member.class);
        given(me.getId()).willReturn(7L);
        given(me.getUuid()).willReturn(MY_UUID);
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

    private Document myDocument(long id) {
        Document d = mock(Document.class);
        given(d.getId()).willReturn(id);
        given(d.getMember()).willReturn(me);
        given(d.isOwnedBy(7L)).willReturn(true);
        return d;
    }

    private static MockMultipartFile pdf() {
        return new MockMultipartFile("file", "note.pdf", "application/pdf", "%PDF-1.4 test".getBytes());
    }

    @Test
    void 삭제_AI_청크_삭제가_성공해야_행을_삭제() {
        Document d = myDocument(5);
        given(documentRepository.findWithMemberById(5L)).willReturn(Optional.of(d));
        given(aiDocumentClient.deleteChunks(5L, MY_UUID)).willReturn(true);

        documentService.delete(5L);

        verify(documentRepository).delete(d);
    }

    @Test
    void 삭제_AI_청크_삭제가_실패하면_행을_남기고_503() {
        Document d = myDocument(5);
        given(documentRepository.findWithMemberById(5L)).willReturn(Optional.of(d));
        given(aiDocumentClient.deleteChunks(5L, MY_UUID)).willReturn(false);

        assertThatThrownBy(() -> documentService.delete(5L))
                .isInstanceOf(BusinessException.class)
                .extracting("errorCode").isEqualTo(ErrorCode.AI_UNAVAILABLE);
        verify(documentRepository, never()).delete(any(Document.class));
    }

    @Test
    void 적재_실패_후_청크_삭제가_성공하면_행을_삭제하고_원래_오류() {
        Document d = myDocument(9);
        given(documentRepository.save(any(Document.class))).willReturn(d);
        given(aiDocumentClient.ingest(anyLong(), anyString(), anyString(), any()))
                .willThrow(new BusinessException(ErrorCode.AI_UNAVAILABLE));
        given(aiDocumentClient.deleteChunks(9L, MY_UUID)).willReturn(true);

        assertThatThrownBy(() -> documentService.upload(pdf()))
                .extracting("errorCode").isEqualTo(ErrorCode.AI_UNAVAILABLE);
        verify(documentRepository).delete(d);
    }

    @Test
    void 적재_타임아웃_후_청크_삭제도_실패하면_행을_INDEXING_으로_남김() {
        Document d = myDocument(9);
        given(documentRepository.save(any(Document.class))).willReturn(d);
        given(aiDocumentClient.ingest(anyLong(), anyString(), anyString(), any()))
                .willThrow(new BusinessException(ErrorCode.AI_UNAVAILABLE));
        given(aiDocumentClient.deleteChunks(9L, MY_UUID)).willReturn(false);

        assertThatThrownBy(() -> documentService.upload(pdf()))
                .extracting("errorCode").isEqualTo(ErrorCode.AI_UNAVAILABLE);
        verify(documentRepository, never()).delete(any(Document.class));
        verify(d, never()).markReady();
    }
}
