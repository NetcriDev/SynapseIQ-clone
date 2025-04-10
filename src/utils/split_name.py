def split_driver_name(name: str):
    """
    Splits a driver's full name into [first_name, middle_name, last_name] 
    following specific rules about hyphens and suffixes like Jr., Sr., III, etc.
    """
    if not isinstance(name, str):
        return [None, None, None]

    name = name.strip()

    if name.lower() == 'unknown' or ('unknown' in name.lower() and len(name) < 10):
        return [None, None, None]

    suffixes = {"sr.", "jr.", "ii", "iii", "iv", "v", "jr"}
    parts = name.split()

    # Normalize all parts to lower for suffix detection
    parts_lower = [p.lower() for p in parts]

    # Rule 3: Handle suffixes (Sr., Jr., III, etc.)
    for i, part in enumerate(parts_lower):
        if part in suffixes and i > 0:
            last_name = parts[i-1]
            parts = parts[:i-1]  # Remove last name and suffix from parts
            break
    else:
        last_name = None

    # Rebuild name after removing suffix, if found
    name_cleaned = ' '.join(parts)

    # Rule 1: Check for "-"
    if "-" in name_cleaned:
        parts = name_cleaned.split()
        # Find the part containing "-"
        for idx, p in enumerate(parts):
            if "-" in p:
                last_name = p
                if ',' not in name_cleaned and len(parts) >= 4:
                    # Rule 2: if 4+ words and no comma
                    middle_name = parts[idx - 1] if idx >= 1 else None
                    first_name = ' '.join(parts[:idx-1]) if idx >= 2 else None
                else:
                    # Default split for hyphen without 4+ words
                    if ',' in name_cleaned:
                        # Format: Last, First Middle
                        last, first_middle = [part.strip() for part in name_cleaned.split(',', 1)]
                        parts = first_middle.split()
                        first_name = parts[0] if len(parts) >= 1 else None
                        middle_name = ' '.join(parts[1:]) if len(parts) > 1 else None
                    else:
                        # Assume last name and rest
                        parts = name_cleaned.split()
                        last_name = p
                        parts.remove(p)
                        first_name = parts[0] if len(parts) >= 1 else None
                        middle_name = ' '.join(parts[1:]) if len(parts) > 1 else None
                break
    else:
        if ',' in name_cleaned:
            # Format: Last, First Middle
            last, first_middle = [part.strip() for part in name_cleaned.split(',', 1)]
            parts = first_middle.split()
            first_name = parts[0] if len(parts) >= 1 else None
            middle_name = ' '.join(parts[1:]) if len(parts) > 1 else None
            last_name = last if not last_name else last_name
        else:
            # Default format: First Middle Last
            parts = name_cleaned.split()
            if len(parts)==2 and not last_name:
                last_name = parts[-1] if len(parts) >= 1 else None
                parts = parts[:-1]
            if not last_name and len(parts)==3:
                last_name = parts[-1] if len(parts) >= 1 else None
                parts = parts[:-1]
            if not last_name and len(parts)>3:
                last_name = parts[-2] if len(parts) >= 1 else None
                parts = parts[:-1]
                parts = parts[:-1]
            first_name = parts[0] if len(parts) >= 1 else None
            middle_name = ' '.join(parts[1:]) if len(parts) > 1 else None

    # Normalize names (capitalize properly)
    def normalize(n):
        return n.title() if isinstance(n, str) else None

    return [normalize(first_name), normalize(middle_name), normalize(last_name)]