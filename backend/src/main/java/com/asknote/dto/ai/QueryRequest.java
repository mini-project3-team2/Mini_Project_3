package com.asknote.dto.ai;

import java.util.List;

/** AI Module 질의 요청 (API 설계서 6.3) — documentIds 는 해당 회원의 READY 문서 id */
public record QueryRequest(String question, String ownerUuid, List<Long> documentIds) {
}
