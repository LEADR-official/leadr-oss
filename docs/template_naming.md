# Board Template Naming

Board templates can automatically generate board names using placeholders and sequential series.

## Placeholders

Use placeholders in the `name_template` field to generate dynamic board names:

| Placeholder     | Output            | Example          |
| --------------- | ----------------- | ---------------- |
| `{year}`        | Four-digit year   | `2025`           |
| `{month}`       | Full month name   | `January`        |
| `{month_short}` | Abbreviated month | `Jan`            |
| `{week}`        | ISO week number   | `42`             |
| `{quarter}`     | Quarter of year   | `Q1`             |
| `{date}`        | ISO date format   | `2025-01-15`     |
| `{series}`      | Sequential number | `1`, `2`, `3`... |

## Sequential Series

The `series` field enables sequential numbering for boards created from the same template:

- **Scoped per template**: Each template maintains its own series sequence
- **Calculated dynamically**: Series values are generated from existing board count + 1
- **Reuses numbers**: If boards are deleted, their numbers become available again

To use series:

1. Set the `series` field to any identifier (e.g., `"weekly"`, `"seasonal"`)
1. Include `{series}` in your `name_template`

## Examples

```json
{
  "name": "Weekly Challenge",
  "name_template": "Week {week} Challenge - {year}",
  "series": null
}
```

**Generates**: "Week 42 Challenge - 2025"

```json
{
  "name": "Monthly Tournament",
  "name_template": "{month} Tournament #{series}",
  "series": "monthly"
}
```

**Generates**: "January Tournament #1", "January Tournament #2"...

```json
{
  "name": "Seasonal Board",
  "name_template": "{year} {quarter} Season",
  "series": null
}
```

**Generates**: "2025 Q1 Season"

## Validation

Templates with invalid placeholders are rejected at creation time. Only the placeholders listed above are supported.
