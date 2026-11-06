package com.asknote.repository;

import com.asknote.entity.ChatHistory;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;

public interface ChatHistoryRepository extends JpaRepository<ChatHistory, Long> {

    /** 내 질문 기록 목록 (페이징, 정렬은 Pageable 로 createdAt desc) */
    Page<ChatHistory> findByMemberId(Long memberId, Pageable pageable);
}
