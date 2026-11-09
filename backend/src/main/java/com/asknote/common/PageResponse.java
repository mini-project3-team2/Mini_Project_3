package com.asknote.common;

import java.util.List;
import org.springframework.data.domain.Page;

/**
 * 페이지 응답의 data (API 설계서 2장)
 * {"content": [], "page": 0, "size": 10, "totalElements": 23, "totalPages": 3}
 * 사용: PageResponse.from(page.map(ChatResponse::from))
 */
public record PageResponse<T>(
        List<T> content,
        int page,
        int size,
        long totalElements,
        int totalPages
) {

    public static <T> PageResponse<T> from(Page<T> page) {
        return new PageResponse<>(
                page.getContent(),
                page.getNumber(),
                page.getSize(),
                page.getTotalElements(),
                page.getTotalPages()
        );
    }
}
