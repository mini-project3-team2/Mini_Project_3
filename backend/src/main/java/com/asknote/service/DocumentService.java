package com.asknote.service;

import com.asknote.client.AiDocumentClient;
import com.asknote.common.auth.CurrentMemberProvider;
import com.asknote.common.exception.BusinessException;
import com.asknote.common.exception.ErrorCode;
import com.asknote.dto.document.DocumentResponse;
import com.asknote.entity.Document;
import com.asknote.entity.Member;
import com.asknote.repository.DocumentRepository;
import java.io.IOException;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.web.multipart.MultipartFile;

/**
 * 자료 업로드 · 삭제
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

    /** 업로드: 행 저장(INDEXING) → AI 적재 → READY. 실패하면 청크 삭제 → 행 삭제 후 오류 (원본은 저장하지 않음) */
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
     * 삭제: AI 청크 삭제 → DB 행 삭제
     * 청크 삭제가 실패해도 행은 삭제한다 — 질문은 DB 의 READY 문서 id 로만 검색하므로 남은 청크는 답변에 쓰이지 않음
     * TODO(IDOR 조치): 현재는 소유자 확인이 없음 → 취약점 재현 캡처 후 fix(security) 커밋에서 403 추가
     */
    public void delete(Long documentId) {
        currentMemberProvider.getCurrentMember();
        Document document = documentRepository.findWithMemberById(documentId)
                .orElseThrow(() -> new BusinessException(ErrorCode.DOCUMENT_NOT_FOUND));

        aiDocumentClient.deleteChunks(document.getId(), document.getMember().getUuid());
        documentRepository.delete(document);
    }

    private void cleanUp(Document document, String ownerUuid) {
        aiDocumentClient.deleteChunks(document.getId(), ownerUuid);
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
