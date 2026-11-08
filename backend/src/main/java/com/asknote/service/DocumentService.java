package com.asknote.service;

import com.asknote.client.AiDocumentClient;
import com.asknote.common.audit.AuditLogger;
import com.asknote.common.auth.CurrentMemberProvider;
import com.asknote.common.exception.BusinessException;
import com.asknote.common.exception.ErrorCode;
import com.asknote.dto.document.DocumentResponse;
import com.asknote.entity.Document;
import com.asknote.entity.Member;
import com.asknote.repository.DocumentRepository;
import java.io.IOException;
import java.util.List;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

/**
 * 자료 목록 · 업로드 · 삭제
 * 메서드에 @Transactional 을 걸지 않는다 — AI 적재(최대 120초) 동안 DB 연결 · 트랜잭션을 붙잡지 않기 위해
 * 각 save · delete 가 리포지토리 단위 트랜잭션으로 바로 커밋된다
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class DocumentService {

    private static final int MAX_FILENAME_LENGTH = 255;

    private final DocumentRepository documentRepository;
    private final CurrentMemberProvider currentMemberProvider;
    private final PdfValidator pdfValidator;
    private final AiDocumentClient aiDocumentClient;
    private final AuditLogger auditLogger;

    /**
     * 내 자료 목록 (최신순, 페이징 없음, status 포함)
     * 회원은 JWT 로만 얻는다 — 요청 값으로 회원을 받지 않으므로 남의 목록은 조회할 수 없음
     */
    public List<DocumentResponse> getMyDocuments() {
        Member member = currentMemberProvider.getCurrentMember();
        return documentRepository.findByMemberIdOrderByCreatedAtDescIdDesc(member.getId()).stream()
                .map(DocumentResponse::from)
                .toList();
    }

    /**
     * 업로드: 행 저장(INDEXING) → AI 적재 → READY. 실패하면 청크 삭제 → 행 삭제 후 오류 (원본은 저장하지 않음)
     * 청크 삭제가 실패하면(타임아웃 후 AI 적재가 아직 진행 중인 경우 등) 행을 INDEXING 으로 남긴다
     * → 사용자가 화면에서 삭제하면 청크 삭제를 다시 시도 (질문은 READY 문서만 검색하므로 답변에 쓰이지 않음)
     * Backend 는 업로드마다 새 문서 id 를 만들므로 AI 의 409(같은 문서 중복 · 적재 중)는 발생하지 않는다
     */
    public DocumentResponse upload(MultipartFile file) {
        Member member = currentMemberProvider.getCurrentMember();
        pdfValidator.validate(file);

        String filename = sanitizeFilename(file.getOriginalFilename());
        byte[] content = readBytes(file);
        Document document = documentRepository.save(new Document(member, filename, file.getSize()));

        try {
            aiDocumentClient.ingest(document.getId(), member.getUuid(), filename, content);
        } catch (BusinessException e) {
            cleanUp(document, member.getUuid());
            throw e;
        }

        document.markReady();
        return DocumentResponse.from(documentRepository.save(document));
    }

    /**
     * 삭제: AI 청크 삭제(204) 확인 후 DB 행 삭제
     * 청크 삭제가 실패하면 행을 남기고 503 AI_UNAVAILABLE — 화면에서는 지워졌는데 AI 저장소에 자료 내용이 남는 일을 막고,
     * 같은 문서 id 로 다시 삭제할 수 있게 한다 (AI 삭제는 청크가 없어도 204 라 재시도해도 안전)
     * IDOR 조치: 로그인 회원의 자료가 아니면 403 (요청의 id 만 믿지 않고 소유자를 DB 에서 확인) + 감사 로그
     */
    public void delete(Long documentId) {
        Member member = currentMemberProvider.getCurrentMember();
        Document document = documentRepository.findWithMemberById(documentId)
                .orElseThrow(() -> new BusinessException(ErrorCode.DOCUMENT_NOT_FOUND));
        if (!document.isOwnedBy(member.getId())) {
            auditLogger.ownershipDenied(member.getEmail(), "DELETE /api/documents/" + documentId);
            throw new BusinessException(ErrorCode.FORBIDDEN);
        }

        if (!aiDocumentClient.deleteChunks(document.getId(), document.getMember().getUuid())) {
            throw new BusinessException(ErrorCode.AI_UNAVAILABLE);
        }
        documentRepository.delete(document);
    }

    private void cleanUp(Document document, String ownerUuid) {
        if (!aiDocumentClient.deleteChunks(document.getId(), ownerUuid)) {
            log.warn("적재 실패 정리 보류 - 청크 삭제 실패로 행을 INDEXING 으로 남김 documentId={}", document.getId());
            return;
        }
        documentRepository.delete(document);
        log.info("적재 실패 정리 완료 documentId={}", document.getId());
    }

    private byte[] readBytes(MultipartFile file) {
        try {
            return file.getBytes();
        } catch (IOException e) {
            throw new BusinessException(ErrorCode.INVALID_INPUT);
        }
    }

    /** 경로 문자 · 제어 문자 제거, 255자 제한 (화면 · 출처 표시용 이름) */
    static String sanitizeFilename(String original) {
        if (original == null || original.isBlank()) {
            return "document.pdf";
        }
        String name = original.replace('\\', '/');
        name = name.substring(name.lastIndexOf('/') + 1);
        name = name.replaceAll("[\\p{Cntrl}]", "").trim();
        if (name.isEmpty()) {
            return "document.pdf";
        }
        return name.length() > MAX_FILENAME_LENGTH ? name.substring(name.length() - MAX_FILENAME_LENGTH) : name;
    }
}
