package com.asknote.dto.chat;

import com.fasterxml.jackson.annotation.JsonIgnoreProperties;

/** 답변 근거 출처 (API 설계서 5.1 sources 항목, page 는 1부터) — 저장된 JSON 에 다른 필드가 있어도 무시 */
@JsonIgnoreProperties(ignoreUnknown = true)
public record ChatSource(
        Long documentId,
        String documentName,
        Integer page
) {
}
