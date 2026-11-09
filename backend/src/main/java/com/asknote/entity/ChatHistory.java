package com.asknote.entity;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.EnumType;
import jakarta.persistence.Enumerated;
import jakarta.persistence.FetchType;
import jakarta.persistence.GeneratedValue;
import jakarta.persistence.GenerationType;
import jakarta.persistence.Id;
import jakarta.persistence.JoinColumn;
import jakarta.persistence.ManyToOne;
import jakarta.persistence.Table;
import java.time.LocalDateTime;
import lombok.AccessLevel;
import lombok.Getter;
import lombok.NoArgsConstructor;
import org.hibernate.annotations.CreationTimestamp;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;

/** 질문 기록. 답변 스트리밍이 정상 완료됐을 때만 저장한다 */
@Entity
@Table(name = "chat_histories")
@Getter
@NoArgsConstructor(access = AccessLevel.PROTECTED)
public class ChatHistory {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY, optional = false)
    @JoinColumn(name = "member_id", nullable = false)
    private Member member;

    @Column(name = "question", nullable = false, length = 1000)
    private String question;

    @Column(name = "answer", nullable = false, columnDefinition = "text")
    private String answer;

    /** 근거 출처 JSON 배열 문자열 [{documentId, documentName, page}] — 문서를 삭제해도 당시 이름이 남음 */
    @Column(name = "sources", columnDefinition = "longtext")
    private String sources;

    @Enumerated(EnumType.STRING)
    @JdbcTypeCode(SqlTypes.VARCHAR)
    @Column(name = "feedback", length = 20)
    private Feedback feedback;

    @CreationTimestamp
    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    public ChatHistory(Member member, String question, String answer, String sourcesJson) {
        this.member = member;
        this.question = question;
        this.answer = answer;
        this.sources = sourcesJson;
    }

    public void updateFeedback(Feedback feedback) {
        this.feedback = feedback;
    }

    public boolean isOwnedBy(Long memberId) {
        return member.getId().equals(memberId);
    }
}
