package com.asknote.repository;

import com.asknote.entity.ChatHistory;
import java.util.Optional;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;

public interface ChatHistoryRepository extends JpaRepository<ChatHistory, Long> {

    /** 내 질문 기록 목록 (페이징, 정렬은 Pageable 로 createdAt desc) */
    Page<ChatHistory> findByMemberId(Long memberId, Pageable pageable);

    /** 피드백용 — 소유자까지 함께 조회 (open-in-view 꺼짐 → 지연 로딩 대신 fetch join) */
    @Query("select c from ChatHistory c join fetch c.member where c.id = :id")
    Optional<ChatHistory> findWithMemberById(@Param("id") Long id);
}
