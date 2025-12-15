## Money & Events

The bank manages house/hotel supply and event logging tracks all key actions and effects.

Example logging flow (automatic inside the engine):

```python
# After actions, events appear in game.event_log
events = game.event_log.get_recent_events()
for ev in events:
    print(ev)
```

### Reference

::: monopoly.money.EventType

::: monopoly.money.GameEvent

::: monopoly.money.EventLog

::: monopoly.money.Bank
