# Preserve Partial Improvements Feature

## Overview

The `preserve_partial_improvements` feature allows AutoFix to preserve code changes even when tests don't pass completely. This is especially useful for onboarding scenarios where users should see immediate value from the service.

## Problem

Previously, AutoFix would revert all changes if tests didn't pass completely, even if some improvements were made. This could be frustrating for users during onboarding, as they wouldn't see any immediate benefit from the service.

## Solution

The new `preserve_partial_improvements` configuration option allows you to control this behavior:

- **Enabled (default)**: Changes are preserved if any improvements are made, even if not all tests pass
- **Disabled**: Changes are only preserved if all tests pass (original behavior)

## Configuration

Add the `preserve_partial_improvements` option to your configuration:

```yaml
# config.yaml
name: "My Test"
file_path: "test_file.py"
max_retries: 3
create_pr: false
pr_strategy: "NONE"
base_branch: "main"
auto_fix: true
preserve_partial_improvements: true  # New option
```

## Use Cases

### 1. Onboarding Scenarios (Recommended: `true`)
When users are first trying your service, you want them to see immediate value:

```yaml
preserve_partial_improvements: true
```

**Benefits:**
- Users see code improvements immediately
- Builds confidence in the service
- Encourages continued usage
- Provides learning opportunities

### 2. Production Environments (Recommended: `false`)
When you need strict quality control:

```yaml
preserve_partial_improvements: false
```

**Benefits:**
- Only accepts complete fixes
- Maintains high code quality standards
- Prevents partial or incomplete changes

### 3. Development Workflows (Recommended: `true`)
During active development when you want to see incremental improvements:

```yaml
preserve_partial_improvements: true
```

## How It Works

The system determines whether to preserve changes based on several factors:

1. **Test Improvements**: Any reduction in test failures
2. **Complete Success**: All tests pass
3. **Configuration**: The `preserve_partial_improvements` setting
4. **Changes Made**: Whether any code changes were actually applied

### Decision Logic

```python
should_preserve_changes = (
    has_any_improvements or 
    best_attempt.status == FixStatus.SUCCESS or
    (len(results['changes']) > 0 and preserve_partial_improvements)
)
```

## Example Scenarios

### Scenario 1: Partial Fix (preserve_partial_improvements: true)
- **Before**: 5 tests failing
- **After**: 2 tests failing, 3 tests passing
- **Result**: Changes preserved ✅
- **Message**: "Code changes were applied successfully. Some improvements were made even if not all tests pass."

### Scenario 2: No Improvement (preserve_partial_improvements: true)
- **Before**: 5 tests failing
- **After**: 5 tests still failing
- **Result**: Changes reverted ❌
- **Message**: "No improvements were made to the code. All changes have been reverted."

### Scenario 3: Complete Success (any setting)
- **Before**: 5 tests failing
- **After**: 0 tests failing
- **Result**: Changes preserved ✅
- **Message**: Success status

## Migration Guide

### From Previous Versions
If you're upgrading from a previous version:

1. **No changes needed**: The feature defaults to `true` for backward compatibility
2. **For strict behavior**: Set `preserve_partial_improvements: false` in your config

### Configuration Examples

```yaml
# Onboarding/Development (default)
preserve_partial_improvements: true

# Production/Strict
preserve_partial_improvements: false

# CLI usage
kaizen autofix --preserve-partial-improvements=true test_file.py
```

## Best Practices

1. **Onboarding**: Always use `true` to show immediate value
2. **CI/CD**: Use `false` for strict quality gates
3. **Development**: Use `true` for iterative improvements
4. **Testing**: Use `false` to ensure complete fixes

## Monitoring

The system provides detailed logging about the decision-making process:

```
INFO: Change preservation decision
{
    'has_any_improvements': True,
    'best_attempt_success': False,
    'changes_made': True,
    'preserve_partial_improvements': True,
    'should_preserve_changes': True
}
```

## Troubleshooting

### Changes Not Preserved
- Check if `preserve_partial_improvements` is set to `true`
- Verify that actual improvements were made
- Review the logs for decision details

### Unexpected Changes Preserved
- Set `preserve_partial_improvements` to `false`
- Check if all tests are actually passing
- Review the improvement analysis

## Future Enhancements

Potential improvements to consider:
- Percentage-based thresholds (e.g., preserve if 80% of tests pass)
- File-specific preservation rules
- Integration with code review workflows
- Custom improvement metrics 