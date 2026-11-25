# Process Flow

## 1. Send Content Flow

```
┌─────────────┐      ┌─────────────┐      ┌──────────────────┐
│   User      │      │   Frontend  │      │   Backend API    │
│  (Sender)   │      │  (Send UI)  │      │  (/api/send)     │
└──────┬──────┘      └──────┬──────┘      └─────────┬────────┘
       │                   │                         │
       │ 1. Enter text/file│                         │
       │    and click Send │                         │
       │───────────────────│────────────────────────>│
       │                   │ 2. Validate input       │
       │                   │ 3. Verify file type     │
       │                   │    (magic bytes)        │
       │                   │ 4. Generate 12-character     │
       │                   │    code (secrets)       │
       │                   │ 5. Write blob to        │
       │                   │    storage              │
       │                   │ 6. Insert metadata to   │
       │                   │    SQLite               │
       │                   │ 7. Return code          │
       │                   │────────────────────────>│
       │                   │                         │
       │<──────────────────│─────────────────────────│
       │ 8. Display code   │                         │
       │    and share link │                         │
       │                   │                         │
       └───────────────────┴─────────────────────────┘
```

## 2. Retrieve Content Flow

```
┌─────────────┐      ┌──────────────────┐      ┌──────────────────┐
│   User      │      │   Frontend UI    │      │   Backend API    │
│  (Receiver) │      │  (Retrieve UI)   │      │  (/api/retrieve) │
└──────┬──────┘      └─────────┬────────┘      └─────────┬────────┘
       │                      │                           │
       │ 1. Enter 12-character     │                           │
       │    code              │                           │
       │──────────────────────│───────────────────────────│
       │                      │ 2. Validate code format   │
       │                      │    (^[A-Za-z0-9]{12}$)              │
       │                      │ 3. Look up in SQLite      │
       │                      │ 4. Check expiry /         │
       │                      │    one-shot status        │
       │                      │ 5. Lazy purge if expired  │
       │                      │ 6. Return metadata + text │
       │                      │───────────────────────────│
       │                      │                           │
       │<─────────────────────│───────────────────────────│
       │ 7. Display content   │                           │
       │    (text/image/file) │                           │
       │                      │                           │
       └──────────────────────┴────────────────────────────┘
```

## 3. Download File Flow

```
┌─────────────┐      ┌──────────────────┐      ┌──────────────────┐      ┌─────────────┐
│   User      │      │   Frontend UI    │      │   Backend API    │      │  Storage    │
│  (Receiver) │      │  (Download Link) │      │  (/api/file)     │      │  (Local/    │
└──────┬──────┘      └─────────┬────────┘      └─────────┬────────┘      │  MinIO)   │
       │                      │                           │               └──────┬──────┘
       │ 1. Click download    │                           │                      │
       │    link              │                           │                      │
       │──────────────────────│───────────────────────────│──────────────────────│
       │                      │ 2. Validate code          │                      │
       │                      │ 3. Stream blob from       │                      │
       │                      │    storage                │                      │
       │                      │ 4. Increment download     │                      │
       │                      │    counter                │                      │
       │                      │ 5. If one-shot:           │                      │
       │                      │    delete blob + row      │                      │
       │                      │───────────────────────────│──────────────────────│
       │                      │                           │                      │
       │<─────────────────────│───────────────────────────│                      │
       │ 6. Save file         │                           │                      │
       │                      │                           │                      │
       └──────────────────────┴────────────────────────────┴──────────────────────┘
```

## 4. Delete Content Flow

```
┌─────────────┐      ┌──────────────────┐      ┌──────────────────┐      ┌─────────────┐
│   User      │      │   Frontend UI    │      │   Backend API    │      │  Storage    │
│  (Sender)   │      │  (Delete Button) │      │  (/api/item)     │      │             │
└──────┬──────┘      └─────────┬────────┘      └─────────┬────────┘      └──────┬──────┘
       │                      │                           │                      │
       │ 1. Click "Delete now"│                           │                      │
       │──────────────────────│───────────────────────────│──────────────────────│
       │                      │ 2. Validate code          │                      │
       │                      │ 3. Delete blob from       │                      │
       │                      │    storage                │                      │
       │                      │ 4. Delete metadata row    │                      │
       │                      │    from SQLite              │                      │
       │                      │ 5. Return 204             │                      │
       │                      │───────────────────────────│──────────────────────│
       │                      │                           │                      │
       │<─────────────────────│───────────────────────────│                      │
       │ 6. Show "Deleted"    │                           │                      │
       │                      │                           │                      │
       └──────────────────────┴────────────────────────────┴──────────────────────┘
```

## 5. Purge Worker Flow

```
┌─────────────────────────────────────────────────────────────────────────┐
│                      BACKGROUND PURGE WORKER                              │
│                      (runs every CLIP_PURGE_INTERVAL seconds)             │
└─────────────────────────────────────────────────────────────────────────┘
                              │
                              ▼
       ┌─────────────────────────────────────────────────────────────┐
       │  1. Query SQLite for expired items:                         │
       │     WHERE expires_at < now OR (one_shot AND retrieved_at)   │
       └─────────────────────────────────────────────────────────────┘
                              │
                              ▼
       ┌─────────────────────────────────────────────────────────────┐
       │  2. For each expired item:                                  │
       │     a. Delete blob from storage (object_key)                │
       │     b. Delete metadata row from SQLite                      │
       │     c. Log purge action                                     │
       └─────────────────────────────────────────────────────────────┘
                              │
                              ▼
       ┌─────────────────────────────────────────────────────────────┐
       │  3. Sleep until next interval                               │
       └─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    (repeat indefinitely)
```

## 6. Lazy Purge on Retrieve

```
Retrieve request for code X
        │
        ▼
   Look up in SQLite
        │
    ┌───┴───┐
    │       │
  Found   Not found
    │       │
    ▼       ▼
Expired?   Return 404
    │
  ┌───┴───┐
  │       │
 Yes     No
  │       │
  ▼       ▼
Delete    Return metadata
blob + row   + content
    │
    ▼
 Return 410 Gone
```

## 7. Error Handling Flow

```
Request received
        │
        ▼
   Validate input
        │
    ┌───┴───┐
    │       │
  Invalid   Valid
    │       │
    ▼       ▼
  400/422   Process request
              │
          ┌───┴───┐
          │       │
        Error   Success
          │       │
          ▼       ▼
        4xx/5xx   200/204
```
