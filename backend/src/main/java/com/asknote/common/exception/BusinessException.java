package com.asknote.common.exception;

import lombok.Getter;

/**
 * 업무 예외 — 서비스에서 throw new BusinessException(ErrorCode.DOCUMENT_NOT_FOUND) 처럼 사용
 * 전역 예외 처리(GlobalExceptionHandler)가 ErrorCode 의 상태 코드 · 문구로 응답한다
 */
@Getter
public class BusinessException extends RuntimeException {

    private final ErrorCode errorCode;
    /** 오류 응답의 data (예: ACCOUNT_LOCKED 의 lockedUntil), 없으면 null */
    private final Object data;

    public BusinessException(ErrorCode errorCode) {
        this(errorCode, null);
    }

    public BusinessException(ErrorCode errorCode, Object data) {
        super(errorCode.getMessage());
        this.errorCode = errorCode;
        this.data = data;
    }
}
