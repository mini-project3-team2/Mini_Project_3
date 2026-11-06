package com.asknote.dto.ai;

/** AI Module 적재 응답 (API 설계서 6.1) */
public record IngestResponse(Long documentId, int chunkCount) {
}
