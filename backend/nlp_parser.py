"""
nlp_parser.py — Natural language processing module for the chatbot interface.

Handles:
- Intent classification (apply_leave, check_balance, cancel_leave, check_status, greeting, help)
- Date extraction from natural language ("next Monday", "July 15", "tomorrow")
- Leave type extraction ("sick leave", "casual", "earned leave")
- Response generation for conversational flow

Uses keyword/pattern matching — no external ML dependencies required.
"""

import re
from datetime import datetime, date, timedelta
from dateutil import parser as dateutil_parser
from dateutil.relativedelta import relativedelta


# ── Intent Classification ──────────────────────────────────────────

INTENT_PATTERNS = {
    'apply_leave': [
        r'\b(apply|request|need|want|take|book|get)\b.*\b(leave|off|day off|time off|holiday)\b',
        r'\b(leave|off|day off)\b.*\b(apply|request|book|want|need)\b',
        r'\b(i am|i\'m|im|feeling)\b.*\b(sick|unwell|not well|ill)\b',
        r'\bnot feeling well\b',
        r'\bneed (a |some )?time off\b',
        r'\bgoing on (a |)(vacation|trip|holiday)\b',
        r'\bfamily (function|event|emergency|matter)\b',
    ],
    'check_balance': [
        r'\b(check|show|view|how many|what is|what\'s|remaining|available)\b.*\b(balance|leaves?|days?)\b',
        r'\b(leave|days?)\b.*\b(balance|left|remaining|available)\b',
        r'\bhow many\b.*\b(days?|leaves?)\b',
    ],
    'cancel_leave': [
        r'\b(cancel|withdraw|revoke|remove)\b.*\b(leave|request|application)\b',
        r'\b(don\'t|dont|do not)\b.*\b(need|want)\b.*\b(leave|off)\b.*\b(anymore|now)\b',
    ],
    'check_status': [
        r'\b(check|what|show|view|track)\b.*\b(status|pending|request)\b',
        r'\b(my|any)\b.*\b(pending|request|application)\b',
        r'\bstatus of\b',
    ],
    'greeting': [
        r'^(hi|hello|hey|good morning|good afternoon|good evening|howdy|sup)\b',
        r'^(namaste|greetings)\b',
    ],
    'help': [
        r'\b(help|what can you|how do i|guide|assist|support)\b',
        r'\bwhat (do you|can you) do\b',
    ],
}


def classify_intent(message):
    """
    Classify the user's message into an intent category.
    Returns the intent string and a confidence score (0-1).
    """
    message_lower = message.lower().strip()

    # Check each intent pattern
    scores = {}
    for intent, patterns in INTENT_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, message_lower):
                scores[intent] = scores.get(intent, 0) + 1

    if not scores:
        return 'unknown', 0.0

    # Return the intent with the highest number of matching patterns
    best_intent = max(scores, key=scores.get)
    confidence = min(1.0, scores[best_intent] / 2.0)  # normalize
    return best_intent, confidence


# ── Date Extraction ────────────────────────────────────────────────

RELATIVE_DATE_PATTERNS = {
    'today': lambda: date.today(),
    'tomorrow': lambda: date.today() + timedelta(days=1),
    'day after tomorrow': lambda: date.today() + timedelta(days=2),
    'yesterday': lambda: date.today() - timedelta(days=1),
}

WEEKDAY_NAMES = {
    'monday': 0, 'mon': 0,
    'tuesday': 1, 'tue': 1, 'tues': 1,
    'wednesday': 2, 'wed': 2,
    'thursday': 3, 'thu': 3, 'thur': 3, 'thurs': 3,
    'friday': 4, 'fri': 4,
    'saturday': 5, 'sat': 5,
    'sunday': 6, 'sun': 6,
}


def _next_weekday(weekday_num):
    """Get the date of the next occurrence of a weekday (0=Monday)."""
    today = date.today()
    days_ahead = weekday_num - today.weekday()
    if days_ahead <= 0:
        days_ahead += 7
    return today + timedelta(days=days_ahead)


def extract_dates(message):
    """
    Extract start_date and end_date from a natural language message.
    Returns (start_date, end_date) as strings in YYYY-MM-DD format,
    or (None, None) if no dates found.
    """
    message_lower = message.lower().strip()
    dates_found = []

    # Check for relative dates
    for phrase, date_fn in RELATIVE_DATE_PATTERNS.items():
        if phrase in message_lower:
            dates_found.append(date_fn())

    # Check for "next <weekday>" or just weekday names
    next_match = re.findall(r'(?:next\s+|this\s+)?(' + '|'.join(WEEKDAY_NAMES.keys()) + r')', message_lower)
    for day_name in next_match:
        day_name = day_name.strip()
        if day_name in WEEKDAY_NAMES:
            dates_found.append(_next_weekday(WEEKDAY_NAMES[day_name]))

    # Check for "next week" without specific day
    if 'next week' in message_lower and not next_match:
        next_monday = _next_weekday(0)
        dates_found.append(next_monday)
        dates_found.append(next_monday + timedelta(days=4))  # full work week

    # Try to parse explicit dates (e.g., "July 15", "15/07/2026", "2026-07-15")
    # Pattern for dates like "July 10 and 11" or "10 and 11 July"
    range_match = re.search(
        r'(\d{1,2})\s*(?:and|to|&|-)\s*(\d{1,2})\s*(?:of\s+)?'
        r'(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|'
        r'jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)',
        message_lower
    )
    if not range_match:
        range_match = re.search(
            r'(jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|'
            r'jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)'
            r'\s*(\d{1,2})\s*(?:and|to|&|-)\s*(\d{1,2})',
            message_lower
        )
        if range_match:
            month_str = range_match.group(1)
            day1 = int(range_match.group(2))
            day2 = int(range_match.group(3))
            year = date.today().year
            try:
                d1 = dateutil_parser.parse(f'{month_str} {day1} {year}').date()
                d2 = dateutil_parser.parse(f'{month_str} {day2} {year}').date()
                dates_found.extend([d1, d2])
            except (ValueError, TypeError):
                pass
    elif range_match:
        day1 = int(range_match.group(1))
        day2 = int(range_match.group(2))
        month_str = range_match.group(3)
        year = date.today().year
        try:
            d1 = dateutil_parser.parse(f'{month_str} {day1} {year}').date()
            d2 = dateutil_parser.parse(f'{month_str} {day2} {year}').date()
            dates_found.extend([d1, d2])
        except (ValueError, TypeError):
            pass

    # Try general date parsing as fallback
    if not dates_found:
        # Look for patterns like "July 15", "15th July", "07/15", etc.
        date_patterns = re.findall(
            r'(\d{1,2}(?:st|nd|rd|th)?\s+(?:of\s+)?'
            r'(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|'
            r'jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)'
            r'(?:\s+\d{4})?)|'
            r'((?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|'
            r'jul(?:y)?|aug(?:ust)?|sep(?:tember)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)'
            r'\s+\d{1,2}(?:st|nd|rd|th)?(?:\s+\d{4})?)|'
            r'(\d{1,2}[/-]\d{1,2}(?:[/-]\d{2,4})?)',
            message_lower
        )
        for match_groups in date_patterns:
            for match in match_groups:
                if match:
                    try:
                        parsed = dateutil_parser.parse(match, dayfirst=False, fuzzy=True).date()
                        if parsed.year < 2000:
                            parsed = parsed.replace(year=date.today().year)
                        dates_found.append(parsed)
                    except (ValueError, TypeError):
                        pass

    if not dates_found:
        return None, None

    # Sort and deduplicate
    dates_found = sorted(set(dates_found))

    start = dates_found[0]
    end = dates_found[-1] if len(dates_found) > 1 else dates_found[0]

    return start.strftime('%Y-%m-%d'), end.strftime('%Y-%m-%d')


# ── Leave Type Extraction ──────────────────────────────────────────

LEAVE_TYPE_PATTERNS = {
    'Casual Leave': [r'\bcasual\b', r'\bcl\b', r'\bpersonal\b'],
    'Sick Leave': [r'\bsick\b', r'\bmedical\b', r'\bhealth\b',
                   r'\b(not feeling well|unwell|ill|fever|cold)\b'],
    'Earned Leave': [r'\bearned\b', r'\bel\b', r'\bprivilege\b',
                     r'\bvacation\b', r'\bannual\b', r'\bplanned\b'],
}


def extract_leave_type(message):
    """
    Extract the leave type from the message text.
    Returns the leave type string or None if not detected.
    """
    message_lower = message.lower()
    for leave_type, patterns in LEAVE_TYPE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, message_lower):
                return leave_type
    return None


# ── Duration Extraction ────────────────────────────────────────────

def extract_duration(message):
    """Extract number of days mentioned in the message."""
    message_lower = message.lower()

    # "X days" pattern
    match = re.search(r'(\d+)\s*(?:days?|day\'?s?)', message_lower)
    if match:
        return int(match.group(1))

    # "a day" or "one day"
    if re.search(r'\b(a day|one day|1 day)\b', message_lower):
        return 1

    # "a couple of days"
    if re.search(r'\b(couple of|two|2)\s*days?\b', message_lower):
        return 2

    # "a few days"
    if re.search(r'\b(few|three|3)\s*days?\b', message_lower):
        return 3

    return None


# ── Reason Extraction ──────────────────────────────────────────────

REASON_PATTERNS = [
    (r'\b(?:because|due to|for|reason[: ]+)\s*(.+?)(?:\.|$)', None),
    (r'\b(family\s+\w+)\b', None),
    (r'\b(not feeling well|feeling sick|fever|unwell)\b', None),
    (r'\b(vacation|trip|travel|wedding|function|ceremony)\b', None),
    (r'\b(personal\s+\w+)\b', None),
    (r'\b(doctor|hospital|appointment|checkup)\b', 'Medical appointment'),
]


def extract_reason(message):
    """Try to extract a reason from the message text."""
    message_lower = message.lower()
    for pattern, override in REASON_PATTERNS:
        match = re.search(pattern, message_lower)
        if match:
            return override if override else match.group(1).strip().capitalize()
    return None


# ── Chatbot Response Generator ─────────────────────────────────────

def generate_chat_response(message, employee_id, conversation_state=None):
    """
    Process a chat message and generate an appropriate response.
    Returns a dict with the response text and any state updates.
    """
    intent, confidence = classify_intent(message)

    if intent == 'greeting':
        return {
            'response': (
                "Hello! 👋 I'm your Leave Management Agent. I can help you with:\n\n"
                "• **Apply for leave** — just tell me the dates and type\n"
                "• **Check your leave balance**\n"
                "• **View request status**\n"
                "• **Cancel a leave request**\n\n"
                "How can I help you today?"
            ),
            'intent': intent,
            'action': None
        }

    if intent == 'help':
        return {
            'response': (
                "Here's what I can do for you:\n\n"
                "📝 **Apply for leave** — Say something like "
                "\"I need casual leave next Thursday and Friday\"\n"
                "📊 **Check balance** — Ask \"How many leaves do I have?\"\n"
                "📋 **View status** — Ask \"Show my pending requests\"\n"
                "❌ **Cancel leave** — Say \"Cancel my leave request\"\n\n"
                "Just type naturally — I'll understand!"
            ),
            'intent': intent,
            'action': None
        }

    if intent == 'check_balance':
        return {
            'response': None,  # handled by the route to fetch real data
            'intent': intent,
            'action': 'fetch_balance',
            'employee_id': employee_id
        }

    if intent == 'check_status':
        return {
            'response': None,
            'intent': intent,
            'action': 'fetch_status',
            'employee_id': employee_id
        }

    if intent == 'apply_leave':
        # Extract details from the message
        leave_type = extract_leave_type(message)
        start_date, end_date = extract_dates(message)
        reason = extract_reason(message)
        duration = extract_duration(message)

        # If we have dates but no explicit duration, calculate it
        if start_date and end_date and not duration:
            d1 = datetime.strptime(start_date, '%Y-%m-%d').date()
            d2 = datetime.strptime(end_date, '%Y-%m-%d').date()
            duration = (d2 - d1).days + 1

        # If we have duration but only one date, calculate end date
        if start_date and not end_date and duration and duration > 1:
            d1 = datetime.strptime(start_date, '%Y-%m-%d').date()
            end_date = (d1 + timedelta(days=duration - 1)).strftime('%Y-%m-%d')

        # If single date and no duration
        if start_date and not end_date:
            end_date = start_date
            duration = 1

        return {
            'response': None,
            'intent': intent,
            'action': 'apply_leave',
            'parsed': {
                'leave_type': leave_type,
                'start_date': start_date,
                'end_date': end_date,
                'num_days': duration,
                'reason': reason,
            },
            'employee_id': employee_id
        }

    if intent == 'cancel_leave':
        return {
            'response': (
                "I can help you cancel a leave request. "
                "Could you tell me which request you'd like to cancel? "
                "You can check your request history on the dashboard for the request details."
            ),
            'intent': intent,
            'action': None
        }

    # Unknown intent
    return {
        'response': (
            "I'm not sure I understood that. Could you rephrase? 🤔\n\n"
            "I can help you **apply for leave**, **check your balance**, "
            "or **view request status**. Just type naturally!"
        ),
        'intent': 'unknown',
        'action': None
    }
