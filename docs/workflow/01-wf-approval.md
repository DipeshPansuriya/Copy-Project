# 01-wf-approval.md

# Workflow: Approval

## 1. Overview

OpenClipboard v1 does **not** have a multi-step approval workflow. Content is sent immediately and retrievable by anyone with the 12-character code.

## 2. Current Behavior

| Step | Action | Actor | System |
|------|--------|-------|--------|
| 1 | User enters text/file and clicks Send | Sender | Frontend → API |
| 2 | API validates and stores content | System | Backend |
| 3 | API returns 12-character code | System | API response |
| 4 | User shares code with receiver | Sender | External channel |
| 5 | Receiver enters code and retrieves | Receiver | API |

No approval gate exists between steps 2 and 3.

## 3. Future Approval Workflow (v2)

If an approval workflow is required, the following states could be introduced:

```
┌─────────────┐    submit    ┌──────────────┐    approve    ┌─────────────┐
│   Draft     │ ───────────► │  Pending   │ ─────────────► │  Approved   │
│   (pending  │               │  (review)  │               │  (live)     │
│   review)   │               │            │               │             │
└─────────────┘               └──────────────┘               └─────────────┘
       │                               │                               │
       │ reject / revoke               │ expire                        │ delete
       ▼                               ▼                               ▼
┌─────────────┐               ┌──────────────┐           ┌─────────────┐
│  Rejected   │               │   Expired    │           │   Deleted   │
│  (removed)  │               │  (purged)    │           │  (purged)   │
└─────────────┘               └──────────────┘           └─────────────┘
```

### Proposed Fields (v2)

| Field | Description |
|-------|-------------|
| `approval_status` | `draft`, `pending`, `approved`, `rejected`, `expired` |
| `approver_id` | User who approved |
| `approved_at` | Timestamp of approval |
| `reject_reason` | Reason for rejection |

### Proposed Endpoints (v2)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/items/{code}/submit` | POST | Submit for approval |
| `/api/items/{code}/approve` | POST | Approve (approver only) |
| `/api/items/{code}/reject` | POST | Reject (approver only) |

## 4. Security Implications

- Approval adds a gate between send and retrieve
- Only approvers can transition `pending` → `approved`
- Unapproved content is not retrievable
- Audit trail records who approved/rejected and when
