"""JSON cleaning utilities."""


class JSONCleaner:
    """Cleans JSON responses from Gemini."""

    @staticmethod
    def clean_comments(json_text: str) -> str:
        """
        Remove JSON comments that Gemini might add.

        Args:
            json_text: JSON text with potential comments

        Returns:
            Clean JSON text
        """
        lines = []
        for line in json_text.split('\n'):
            if '#' not in line:
                lines.append(line)
                continue

            in_string = False
            quote_char = None
            clean_line = []

            for i, char in enumerate(line):
                if char in ('"', "'") and (i == 0 or line[i-1] != '\\\\'):
                    if not in_string:
                        in_string = True
                        quote_char = char
                    elif char == quote_char:
                        in_string = False
                        quote_char = None

                if char == '#' and not in_string:
                    break
                clean_line.append(char)

            lines.append(''.join(clean_line).rstrip())

        return '\\n'.join(lines)

    @staticmethod
    def strip_markdown(json_text: str) -> str:
        """
        Remove markdown code blocks from JSON.

        Args:
            json_text: JSON text with potential markdown

        Returns:
            Clean JSON text
        """
        json_text = json_text.strip()

        if json_text.startswith('```'):
            lines = json_text.split('\\n', 1)
            if len(lines) > 1:
                json_text = lines[1]

        if json_text.endswith('```'):
            json_text = json_text.rsplit('\\n```', 1)[0]

        return json_text.strip()
