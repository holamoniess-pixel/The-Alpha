# RAVER Sentinel Deployment Guide

## Quick Start

### Prerequisites
- Python 3.9+
- Node.js 16+
- Windows 10/11 (for full functionality)

### Installation

1. **Clone and Setup**
   ```bash
   cd "c:\Users\Pince N ClawBot\Desktop\The Alpha"
   ```

2. **Install Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Install Node.js Dependencies**
   ```bash
   cd apps/ui
   npm install
   cd ../..
   ```

### Starting the System

1. **Start Backend API**
   ```bash
   python apps/api/main.py
   ```
   - API will be available at http://localhost:8000
   - WebSocket endpoint: ws://localhost:8000/ws

2. **Start Frontend UI**
   ```bash
   cd apps/ui
   npm start
   ```
   - UI will be available at http://localhost:3000

### Default Credentials
- **Admin**: admin / admin123
- **User**: user / user123

## Architecture Overview

### Core Components

1. **RAVER Core Orchestrator** (`packages/raver-core/`)
   - Intent parsing and policy evaluation
   - System pause/resume functionality
   - Audit logging with tamper-evidence

2. **RAVER Vault** (`packages/raver-vault/`)
   - AES-256-GCM encrypted storage
   - Role-based access control
   - SQLite backend with secure key derivation

3. **Gateway API** (`apps/api/`)
   - FastAPI backend with WebSocket support
   - Authentication and authorization
   - Real-time event streaming

4. **React UI** (`apps/ui/`)
   - Material-UI based interface
   - Real-time status updates
   - System control dashboard

### Safety Features

- **Policy Engine**: Risk-based approval system
- **Audit Logging**: Tamper-evident logging with hash chains
- **System Pause**: Emergency stop with user control
- **Role-Based Access**: Granular permissions system

## Configuration

### Environment Variables
```bash
# API Configuration
RAVER_API_HOST=0.0.0.0
RAVER_API_PORT=8000

# Vault Configuration
RAVER_VAULT_PATH=./raver_vault.db
RAVER_VAULT_KEY_DERIVATION=pbkdf2

# Security Configuration
RAVER_SESSION_TIMEOUT=30
RAVER_REQUIRE_APPROVAL=true
```

### Policy Rules
Policy rules are stored in `policy_rules.json` and can be customized:
- Risk levels: LOW, MEDIUM, HIGH, CRITICAL
- Approval methods: NONE, UI_CONFIRM, VOICE_REAUTH, BIOMETRIC
- Role-based permissions

## Development

### Project Structure
```
apps/
├── api/           # FastAPI backend
├── ui/            # React frontend
└── worker-link-sandbox/  # Link inspection worker

packages/
├── raver-core/    # Orchestrator and policy engine
├── raver-sentinel/ # Security monitoring
├── raver-vault/   # Encrypted storage
├── raver-hal/      # Hardware abstraction layer
└── raver-shared/   # Common schemas and IPC
```

### Running Tests
```bash
# Python tests
python -m pytest packages/

# Node.js tests
cd apps/ui && npm test
```

## Security Considerations

1. **Network Security**
   - All API endpoints require authentication
   - WebSocket connections are authenticated
   - CORS configured for production domains

2. **Data Protection**
   - Vault uses AES-256-GCM encryption
   - Keys derived with PBKDF2 (100,000 iterations)
   - Audit logs are tamper-evident

3. **Access Control**
   - Role-based permissions (ADMIN, USER, GUEST)
   - Policy-driven approval system
   - Session management with timeouts

## Troubleshooting

### Common Issues

1. **Module Import Errors**
   ```bash
   # Ensure Python path includes packages
   export PYTHONPATH="${PYTHONPATH}:./packages"
   ```

2. **Database Connection Issues**
   ```bash
   # Check SQLite permissions
   ls -la raver_vault.db
   ```

3. **WebSocket Connection Failures**
   - Check firewall settings
   - Verify API is running on port 8000
   - Ensure CORS allows localhost:3000

### Logs
- API logs: Console output
- UI logs: Browser developer tools
- Audit logs: `raver_audit.db`

## Production Deployment

### Security Hardening
1. Use HTTPS in production
2. Configure proper CORS origins
3. Set strong vault passwords
4. Enable file system encryption
5. Configure Windows Firewall rules

### Performance Optimization
1. Use production build of React app
2. Configure reverse proxy (nginx/Apache)
3. Enable database connection pooling
4. Monitor system resources

## Support

For issues and questions:
1. Check audit logs for error details
2. Review system status in dashboard
3. Verify network connectivity
4. Check configuration files

## License

MIT License - See LICENSE file for details.
