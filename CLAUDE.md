# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Context

A **cryptocurrency futures trading system** with real-time market monitoring and automated trading capabilities for Binance and Bybit exchanges. Built with PyQt5 GUI and event-driven architecture.

## Essential Commands

```bash
# Run the trading system with GUI
python main.py

# Core test suites
python test_integration.py      # Module initialization and dependency tests
python test_realtime.py         # Real-time data flow and signal processing
python test_gui_headless.py     # GUI component tests (may show warnings in headless mode)

# API and connection tests
python test_futures_connection.py  # Test Binance futures API connectivity
python test_api_direct.py          # Direct API testing without GUI
python test_binance_connector.py   # Binance connector functionality
python test_balance.py             # Account balance retrieval
python test_price_events.py        # Price update event system

# GUI-specific tests
python test_trading_gui.py      # Trading interface components
python test_gui_api.py          # GUI-API integration

# System monitoring
python monitor_trading.py       # Real-time trading monitor with live updates

# Check system logs
type trading_system.log         # Windows
cat trading_system.log          # Unix/Mac
```

## Architecture Overview

### Event-Driven Core
The system uses a **centralized event bus** pattern where components communicate through events rather than direct calls:

```
Market Data → EventSystem → SignalProcessor → TradingEngine → Exchange API
                ↓                    ↓              ↓
              GUI Updates      Condition Check   Order Execution
```

### Critical Module Dependencies

1. **`core/trading_engine.py`** - Central orchestrator that:
   - Maintains `entry_conditions` and `exit_conditions` lists
   - Processes signals from `SignalProcessor`
   - Executes trades via exchange APIs
   - Must have `set_combination_mode()`, `set_risk_manager()`, `set_time_control()` methods

2. **`core/event_system.py`** - Singleton message bus:
   - All real-time data flows through this
   - GUI updates subscribe to events here
   - Handles `TICK_DATA`, `CANDLE_DATA`, `SIGNAL`, `TRADE` events

3. **`gui/main_window.py`** - Main application window:
   - Initializes API clients in `_init_api_clients()`
   - Updates BTC price via `update_btc_price()` every 5 seconds
   - Falls back to Binance public API if no API keys configured

### GUI-Logic Connection Pattern

All GUI widgets follow this connection pattern:
```python
# In each tab's connect_signals():
widget.stateChanged.connect(self.update_xxx)
widget.valueChanged.connect(self.update_xxx)

# update_xxx() then calls:
self.trading_engine.add_entry_condition(condition)
self.trading_engine.set_risk_manager(risk_manager)
```

## Critical Implementation Details

### Module Initialization Order

The system requires specific initialization sequence:
1. `SettingsManager` (singleton) loads `config.json`
2. `EventSystem` (singleton) initializes event bus
3. API clients created based on config credentials
4. `TradingEngine` initialized with API connectors
5. GUI components subscribe to events

### GUI Widget Specifications

**PCS Table Column Widths** (must be exact for Korean text display):
- Step: 40px
- Active: 50px
- Take Profit: 60px
- Stop Loss: 60px
- STEP: 80px
- Status: 80px (required for "모니터링" text)

**Color Constants** (in `config/constants.py`):
- Must include: `primary`, `primary_light`, `danger`, `danger_light`, `success`, `success_light`

### API Client Initialization

The system attempts API connections in this order:
1. Load credentials from `config.json` via `SettingsManager`
2. Create authenticated clients if keys exist
3. Fall back to public APIs for price data only

### Condition Factory Pattern

New conditions must:
1. Inherit from `BaseCondition`
2. Accept `name` and `config` in `__init__`
3. Call `super().__init__(name, config)`
4. Implement `evaluate(market_data, position=None)`

## Configuration Structure

`config.json` managed by `SettingsManager` contains:
```json
{
  "exchanges": [
    {
      "name": "binance",
      "api_key": "",
      "api_secret": "",
      "testnet": true
    }
  ],
  "trading": {...},
  "entry": {...},
  "exit": {...},
  "risk": {...}
}
```

Access via: `settings_manager.get_exchange_config("binance")`

### Exchange API Structure

- **Base**: `api/base_api.py` - `BaseAPIConnector` abstract class
- **Binance**: `api/binance/futures_client.py` - Futures trading implementation
- **Bybit**: `api/bybit/futures_client.py` - Alternative exchange support
- All API methods return standardized models from `core/models.py`

## Widget Helper Methods

All tabs inheriting from `BaseTab` need these helpers if using styled widgets:
```python
def create_group_box(self, title: str) -> QGroupBox
def create_button(self, text: str, style: str) -> QPushButton
```

## Real-time Data Flow

1. `DataManager` generates/fetches market data
2. Published via `EventSystem.publish("TICK_DATA", data)`
3. `SignalProcessor` evaluates all conditions
4. Signals trigger `TradingEngine` actions
5. GUI updates via Qt signals (`pyqtSignal`)

## Language Note

The system uses **Korean language** for UI labels and logging. Key terms:
- 진입 (Entry)
- 청산 (Exit/Close)
- 포지션 (Position)
- 레버리지 (Leverage)
- 모니터링 (Monitoring)

## Dependencies

Core requirements:
- PyQt5==5.15.10 (NOT PyQt6)
- numpy>=1.26.4
- pandas>=2.3.2
- requests>=2.31.0

## Windows-Specific Considerations

- Use absolute paths with forward slashes or raw strings
- GUI encoding issues possible - logs may show garbled Korean text
- Use `start /B python main.py` for background execution

## Common Troubleshooting

### API Connection Issues
- Check `config.json` for valid API credentials
- Verify testnet mode matches API keys (testnet vs mainnet)
- System falls back to public API for price data if no keys configured

### GUI Not Displaying Properly
- Ensure PyQt5==5.15.10 (not PyQt6)
- Check Korean font support for proper text rendering
- Verify column widths in PCS table match specifications

### Test Failures
- Run `test_integration.py` first to verify module dependencies
- API tests require valid credentials in `config.json`
- Headless GUI tests may show Qt warnings - this is normal