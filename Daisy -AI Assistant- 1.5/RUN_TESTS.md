# Running Tests - Quick Reference

## Correct Path

The Daisy Assistant 0.6 folder is located at:
```
/Users/phktistakis/Devoloper Projects/Daisy -AI Assistant-/Daisy -AI Assistant- 0.6
```

## Quick Commands

### Navigate to the directory:
```bash
cd "/Users/phktistakis/Devoloper Projects/Daisy -AI Assistant-/Daisy -AI Assistant- 0.6"
```

**Note**: The quotes are important because the path contains spaces!

### Run all tests:
```bash
python3 tests/run_tests.py
```

### Run integration demo:
```bash
python3 tests/demo_integration.py
```

## One-Liner (from home directory)

```bash
cd "/Users/phktistakis/Devoloper Projects/Daisy -AI Assistant-/Daisy -AI Assistant- 0.6" && python3 tests/run_tests.py
```

## Expected Results

### Test Suite:
- ✅ **40 tests passing**
- ⚠️ **1 test with minor issue** (not a functionality problem)
- 📊 **97.6% pass rate**

### Integration Demo:
- ✅ All 5 demos complete successfully
- Shows schema validation, safety checking, action execution, brain parsing, and persistence

## Alternative: Create an alias

Add this to your `~/.zshrc`:
```bash
alias daisy-test='cd "/Users/phktistakis/Devoloper Projects/Daisy -AI Assistant-/Daisy -AI Assistant- 0.6" && python3 tests/run_tests.py'
alias daisy-demo='cd "/Users/phktistakis/Devoloper Projects/Daisy -AI Assistant-/Daisy -AI Assistant- 0.6" && python3 tests/demo_integration.py'
```

Then reload:
```bash
source ~/.zshrc
```

Now you can just run:
```bash
daisy-test
daisy-demo
```



