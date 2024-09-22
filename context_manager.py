class ContextManager:
    def __init__(self):
        self.dialogue_state = {}
        self.current_topic = None
        self.user_id = None
        self.topic_mapping = {  # **Add this block**
            "market": "market",
            "valuation": "valuation",
            "inspection": "inspection",
            "transaction": "transaction",
            "financing": "financing",
            "ownership": "ownership",
            "investment": "investment",
            "legal": "legal",
            "professional": "professional",
            "platform": "platform"
        }

    def update_context(self, user_input, intents):
        detected_topic = self._determine_topic(intents)
        if detected_topic != self.current_topic:
            # Handle topic shift
            self.current_topic = detected_topic

    def _determine_topic(self, intents):
        # Implement logic to determine the topic based on intents
        if not intents:
            return self.current_topic  # Remain on the current topic if no new intents found
        # Example logic
        for intent in intents:
            if intent in self.topic_mapping:
                return self.topic_mapping[intent]
        return 'general'