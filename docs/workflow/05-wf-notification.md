# 05-wf-notification.md

# Workflow: Notification

## 1. Current State (v1)

OpenClipboard v1 does **not** send notifications. The 12-character code is the only mechanism for connecting sender and receiver. The sender must share the code through an external channel (email, chat, SMS, in-person, etc.).

## 2. Current Notification Flow (Manual)

```
┌─────────────┐      External Channel      ┌─────────────┐
│   Sender    │ ─────────────────────────► │   Receiver  │
│             │     (email, chat, SMS,     │             │
│             │      in-person, etc.)      │             │
└─────────────┘                            └─────────────┘
       │                                           │
       │  Shares 12-character code                      │  Enters code
       │                                           │   and retrieves
       └───────────────────────────────────────────┘
```

## 3. Future Notification Workflow (v2)

If notifications are added, the following channels could be supported:

### Notification Types

| Type | Trigger | Channel | Recipient |
|------|---------|---------|-----------|
| Code delivery | After send | Email / SMS | Receiver |
| Expiry warning | TTL - 1 hour | Email | Sender |
| Content retrieved | After download | Email / Webhook | Sender |
| Content deleted | After delete | Email / Webhook | Sender |
| Content expired | After purge | Email / Webhook | Sender |

### Notification Flow

```
┌─────────────┐      ┌──────────────────┐      ┌──────────────────┐
│   Sender    │      │   Backend API    │      │  Notification    │
│             │      │  (/api/send)     │      │  Service         │
└──────┬──────┘      └─────────┬────────┘      └─────────┬────────┘
       │                      │                           │
       │ 1. Send content      │                           │
       │──────────────────────│───────────────────────────│
       │                      │ 2. Store content          │
       │                      │ 3. Trigger notification   │
       │                      │    (async)                │
       │                      │───────────────────────────│
       │                      │                           │
       │                      │───────────────────────────│
       │                      │                           │
       │                      │      4. Send email/SMS    │
       │                      │      to receiver with     │
       │                      │      the 12-character code     │
       │                      │                           │
       │                      │───────────────────────────│
       │                      │                           │
       │<─────────────────────│───────────────────────────│
       │ 5. Return code       │                           │
       │                      │                           │
       └──────────────────────┴────────────────────────────┘
```

### Proposed Endpoints (v2)

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/notifications/preferences` | GET/PUT | User notification settings |
| `/api/notifications/history` | GET | Notification history |
| `/api/webhooks` | GET/POST/DELETE | Webhook management |

### Proposed Channels

| Channel | Provider Example | Use Case |
|---------|-----------------|----------|
| Email | SMTP, SendGrid, AWS SES | Code delivery, expiry warnings |
| SMS | Twilio, AWS SNS | Code delivery |
| Webhook | Generic HTTP | System integrations |
| Slack | Slack API | Team notifications |

### Configuration (v2)

```env
NOTIFICATION_CHANNEL=email
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=notifications@example.com
SMTP_PASSWORD=change-me
NOTIFICATION_FROM=noreply@example.com

# Webhook
WEBHOOK_URL=https://hooks.example.com/clipboard
WEBHOOK_SECRET=change-me
```

## 4. Privacy Considerations

- Notifications contain the 12-character code (capability token)
- Email/SMS delivery exposes codes to third-party providers
- Consider end-to-end encrypted delivery for sensitive content
- Allow users to opt out of notifications

## 5. Retry Policy (Future)

| Failure | Retry | Backoff |
|---------|-------|---------|
| Email bounce | 3 attempts | Exponential |
| SMS failure | 3 attempts | Exponential |
| Webhook timeout | 5 attempts | Linear |
| Notification service down | Queue and retry later | — |
