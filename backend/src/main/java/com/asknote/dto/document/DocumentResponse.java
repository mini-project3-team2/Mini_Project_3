package com.asknote.dto.document;

import com.asknote.entity.Document;
import java.time.LocalDateTime;
import java.time.temporal.ChronoUnit;

/** 자료 응답 (업로드 201 · 목록 공용, API 설계서 4.1 · 4.2) */
public record DocumentResponse(
        Long id,
        String originalFilename,
        long fileSize,
        String status,
        LocalDateTime createdAt
) {

    public static DocumentResponse from(Document document) {
        return new DocumentResponse(
                document.getId(),
                document.getOriginalFilename(),
                document.getFileSize(),
                document.getStatus().name(),
                document.getCreatedAt() == null ? null : document.getCreatedAt().truncatedTo(ChronoUnit.SECONDS));
    }
}
