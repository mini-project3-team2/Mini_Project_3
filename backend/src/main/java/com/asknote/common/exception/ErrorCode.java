package com.asknote.common.exception;

import lombok.Getter;
import org.springframework.http.HttpStatus;

/**
 * 오류 코드 (API 설계서 · mock-data/responses 와 같은 코드 · 문구)
 * 새 코드가 필요하면 여기에 추가하고 API 설계서에도 반영한다
 */
@Getter
public enum ErrorCode {

    // 400
    INVALID_INPUT(HttpStatus.BAD_REQUEST, "입력값을 확인해 주세요"),
    INVALID_FILE_TYPE(HttpStatus.BAD_REQUEST, "PDF 파일만 올릴 수 있습니다"),
    EMPTY_FILE(HttpStatus.BAD_REQUEST, "빈 파일은 올릴 수 없습니다"),
    NO_DOCUMENT(HttpStatus.BAD_REQUEST, "답변에 쓸 수 있는 자료가 아직 없습니다. 자료를 먼저 올려 주세요"),

    // 401
    UNAUTHORIZED(HttpStatus.UNAUTHORIZED, "로그인이 필요합니다"),
    INVALID_CREDENTIALS(HttpStatus.UNAUTHORIZED, "이메일 또는 비밀번호가 올바르지 않습니다"),
    INVALID_REFRESH_TOKEN(HttpStatus.UNAUTHORIZED, "다시 로그인해 주세요"),

    // 403
    FORBIDDEN(HttpStatus.FORBIDDEN, "접근 권한이 없습니다"),

    // 404
    NOT_FOUND(HttpStatus.NOT_FOUND, "요청한 주소를 찾을 수 없습니다"),
    DOCUMENT_NOT_FOUND(HttpStatus.NOT_FOUND, "자료를 찾을 수 없습니다"),
    CHAT_NOT_FOUND(HttpStatus.NOT_FOUND, "질문 기록을 찾을 수 없습니다"),

    // 405
    METHOD_NOT_ALLOWED(HttpStatus.METHOD_NOT_ALLOWED, "지원하지 않는 요청 방식입니다"),

    // 409
    DUPLICATE_EMAIL(HttpStatus.CONFLICT, "이미 가입된 이메일입니다"),

    // 413
    FILE_TOO_LARGE(HttpStatus.CONTENT_TOO_LARGE, "파일 크기는 10MB 이하여야 합니다"),

    // 422
    TEXT_EXTRACTION_FAILED(HttpStatus.UNPROCESSABLE_CONTENT, "문서에서 글자를 읽지 못했습니다. 스캔한 PDF는 지원하지 않습니다"),

    // 423
    ACCOUNT_LOCKED(HttpStatus.LOCKED, "로그인에 여러 번 실패해 계정이 잠겼습니다. 잠시 후 다시 시도해 주세요"),

    // 500
    INTERNAL_SERVER_ERROR(HttpStatus.INTERNAL_SERVER_ERROR, "일시적인 오류가 발생했습니다"),

    // 503
    AI_UNAVAILABLE(HttpStatus.SERVICE_UNAVAILABLE, "지금은 자료를 처리할 수 없습니다. 잠시 후 다시 시도해 주세요");

    private final HttpStatus status;
    private final String message;

    ErrorCode(HttpStatus status, String message) {
        this.status = status;
        this.message = message;
    }
}
