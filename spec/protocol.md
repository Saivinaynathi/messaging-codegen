# Messaging Protocol Specification

## 1. Purpose

This document defines the platform-independent messaging protocol.

All generated clients MUST follow this specification.

Platform-specific implementations MUST NOT change the behavior defined here.

## 2. User Identity

A user identifies themselves by entering a non-empty display name on first
launch.

Example:

Alice

The client MUST store the name locally so the user does not need to enter it
again on subsequent launches.

User names are case-sensitive.

Authentication and passwords are outside the scope of this project.

## 3. Message Model

Every message MUST contain:

- message_id
- sender
- recipient
- text
- created_at

Example:

```json
{
  "message_id": "550e8400-e29b-41d4-a716-446655440000",
  "sender": "Alice",
  "recipient": "Bob",
  "text": "Hi Bob, I have something important to tell you",
  "created_at": "2026-10-05T20:00:00Z"
}
