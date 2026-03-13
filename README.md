# RAVER Sentinel System

A secure, production-oriented AI assistant system with defensive "Sentinel" security layer, encrypted vault storage, and comprehensive policy governance.

## Overview

RAVER Sentinel combines autonomous assistant capabilities with enterprise-grade security features:

- **Core Orchestrator**: Intent processing, tool routing, and policy enforcement
- **Sentinel Security Layer**: Real-time monitoring and threat detection
- **Encrypted Vault**: AES-256-GCM encrypted secret storage with role-based access
- **Policy Engine**: Zero-trust execution with approval workflows
- **Modern UI**: React-based interface with real-time WebSocket updates
- **System Control**: Pause/resume functionality with full user control

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   RAVER UI      │    │  Gateway API    │    │ Core Orchestrator│
│   (React)       │◄──►│   (FastAPI)     │◄──►│   (Service)     │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                                       │
                       ┌─────────────────┐    ┌─────────────────┐
                       │   RAVER Vault   │    │  Policy Engine  │
                       │ (Encrypted)     │    │ (Risk Scoring) │
                       └─────────────────┘    └─────────────────┘
```

## Features

### 🔒 Security & Governance
- **Zero-Trust Execution**: Every action requires policy evaluation and approval
- **Role-Based Access Control**: Granular permissions with capability matrix
- **Tamper-Evident Audit**: Append-only logging with cryptographic verification
- **Encrypted Storage**: AES-256-GCM with secure key derivation

### ⚡ System Control
- **Pause/Resume**: Instant system halt with user confirmation
- **Manual Approvals**: UI-based approval workflow for high-risk actions
- **Real-time Monitoring**: WebSocket updates for system status
- **Emergency Stop**: Immediate termination of all automated operations

### 🛡️ Sentinel Protection
- **Behavior Guard**: Ransomware and suspicious activity detection
- **Windows Integration**: Defender handshake and Event Log monitoring
- **Network Security**: Phishing link isolation and sandboxing
- **DLP Monitoring**: Optional data loss prevention

### 📦 Vault Management
- **Secure Storage**: Encrypted credential and secret management
- **Access Policies**: Time-based, IP-restricted, role-based access
- **Audit Trail**: Complete access logging with forensic capabilities
- **Key Rotation**: Automated master key rotation support

## Quick Start

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   npm install
   ```

2. Initialize the vault:
   ```bash
   python -m raver_vault init
   ```

3. Start services:
   ```bash
   python -m apps.api.main
   npm run dev
   ```

## Project Structure

```
apps/
  api/           # FastAPI Gateway
  ui/            # React frontend
  worker-link-sandbox/  # Link inspection worker
packages/
  raver-core/    # Orchestrator and policy engine
  raver-sentinel/ # Security monitoring
  raver-vault/   # Encrypted storage
  raver-hal/      # Hardware abstraction layer
  raver-shared/   # Common schemas and IPC
```

## License

MIT License - See LICENSE file for details
