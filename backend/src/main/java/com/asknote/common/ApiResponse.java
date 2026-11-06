package com.asknote.common;

import com.asknote.common.exception.ErrorCode;
import com.fasterxml.jackson.annotation.JsonInclude;

/**
 * 공통 응답 형식 (API 설계서 2장)
 * 성공: {"success": true, "data": {...}, "message": ""}
 * 실패: {"success": false, "data": null, "message": "...", "code": "..."}
 */
public record ApiResponse<T>(
        boolean success,
        T data,
        String message,
        @JsonInclude(JsonInclude.Include.NON_NULL) String code
) {

    public static <T> ApiResponse<T> ok(T data) {
        return new ApiResponse<>(true, data, "", null);
    }

    public static <T> ApiResponse<T> ok(T data, String message) {
        return new ApiResponse<>(true, data, message, null);
    }

    public static ApiResponse<Object> fail(ErrorCode errorCode) {
        return new ApiResponse<>(false, null, errorCode.getMessage(), errorCode.name());
    }

    public static ApiResponse<Object> fail(ErrorCode errorCode, Object data, String message) {
        return new ApiResponse<>(false, data, message, errorCode.name());
    }
}
