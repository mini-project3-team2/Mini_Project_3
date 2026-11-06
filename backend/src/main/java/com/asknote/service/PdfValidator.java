package com.asknote.service;

import org.springframework.stereotype.Component;
import org.springframework.web.multipart.MultipartFile;

/**
 * 업로드 파일 검증 (API 설계서 4.1) — 구현 담당: Backend 2
 * - 빈 파일 → BusinessException(ErrorCode.EMPTY_FILE)
 * - 확장자 .pdf 가 아니거나, 파일 앞 5바이트가 "%PDF-" 가 아니면 → BusinessException(ErrorCode.INVALID_FILE_TYPE)
 * (10MB 초과는 spring.servlet.multipart 설정이 먼저 막고 전역 예외 처리가 413 으로 응답)
 */
@Component
public class PdfValidator {

    public void validate(MultipartFile file) {
        // TODO(Backend 2): 위 규칙대로 구현
    }
}
