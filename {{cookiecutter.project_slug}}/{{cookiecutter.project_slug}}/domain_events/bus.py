from collections import defaultdict


class EventBus:
    """
    A simple in-memory pub-sub mechanism for domain events.
    """

    def __init__(self):
        # Dictionary where key=EventClass, value=list of handler callables
        self._subscribers = defaultdict(list)

    def subscribe(self, event_type, handler):
        """
        Register a handler for a given event_type.
        event_type: a class of DomainEvent
        handler: a callable with signature handler(event)
        """
        self._subscribers[event_type].append(handler)

    def publish(self, event):
        """
        Publish an event to all subscribers.
        """
        event_type = type(event)
        handlers = self._subscribers.get(event_type, [])
        for handler in handlers:
            handler(event)


event_bus = EventBus()
