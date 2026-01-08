# Contributing to SEC Earnings Growth Analyzer

Thank you for your interest in contributing! This document provides guidelines for contributing to this project.

## How to Contribute

### Reporting Issues

If you find a bug or have a feature request:

1. Check the [existing issues](https://github.com/yourusername/sec-earnings-analyzer/issues) to avoid duplicates
2. Create a new issue with:
   - Clear, descriptive title
   - Detailed description of the problem/feature
   - Steps to reproduce (for bugs)
   - Expected vs. actual behavior
   - Your environment (Python version, OS, etc.)

### Submitting Code

1. **Fork the repository**
2. **Create a feature branch**
   ```bash
   git checkout -b feature/your-feature-name
   ```

3. **Make your changes**
   - Write clean, documented code
   - Follow existing code style
   - Add tests if applicable
   - Update documentation

4. **Test your changes**
   ```bash
   python sec_data_extractor.py  # Basic functionality test
   streamlit run streamlit_app.py  # Dashboard test
   ```

5. **Commit with clear messages**
   ```bash
   git commit -m "Add feature: [description]"
   ```

6. **Push and create a Pull Request**
   ```bash
   git push origin feature/your-feature-name
   ```

## Code Style Guidelines

### Python Code
- Follow PEP 8 style guide
- Use type hints where appropriate
- Write docstrings for functions and classes
- Keep functions focused and < 50 lines when possible
- Use meaningful variable names

### Example:
```python
def calculate_metric(revenue: float, cost: float) -> float:
    """
    Calculate profit margin.
    
    Args:
        revenue: Total revenue
        cost: Total cost
        
    Returns:
        Profit margin as decimal (0.0 to 1.0)
    """
    if revenue == 0:
        return 0.0
    return (revenue - cost) / revenue
```

### Commit Messages
- Use present tense ("Add feature" not "Added feature")
- Be descriptive but concise
- Reference issues when applicable (#123)

Examples:
- `Add support for IFRS filings`
- `Fix bug in quarterly decomposition logic (#45)`
- `Improve error handling for missing data`

## Development Setup

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/sec-earnings-analyzer.git
cd sec-earnings-analyzer
```

### 2. Create virtual environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Set environment variables
```bash
export SEC_USER_AGENT="YourName your.email@example.com"
```

## Testing

Currently, this project uses manual testing. When adding new features:

1. Test with multiple tickers (at least 3-5)
2. Test edge cases (missing data, negative values, etc.)
3. Verify dashboard renders correctly
4. Check CSV output format

**Future enhancement**: Add automated unit tests using pytest.

## Enhancement Ideas

Looking for ways to contribute? Here are some feature ideas:

### Priority Features
- [ ] Add unit tests with pytest
- [ ] Support for international filings (IFRS)
- [ ] Integrate analyst estimates (earnings surprises)
- [ ] Add more industry-specific metrics
- [ ] Implement caching for faster re-runs
- [ ] Build backtesting framework
- [ ] Add real-time filing alerts

### Dashboard Enhancements
- [ ] Sector comparison charts
- [ ] Correlation heatmaps
- [ ] Outlier detection visualization
- [ ] Export to Excel with formatting
- [ ] PDF report generation
- [ ] User-defined metric calculations

### Data Quality
- [ ] Automatic outlier flagging
- [ ] M&A detection from 8-K filings
- [ ] Non-GAAP reconciliation parsing
- [ ] Data validation rules engine

### Performance
- [ ] Parallel processing for multiple tickers
- [ ] Database backend (PostgreSQL)
- [ ] Incremental updates (only fetch new data)
- [ ] Compressed data storage (Parquet)

## Documentation

When adding features, please update:
- README.md (if user-facing feature)
- METHODOLOGY.md (if changing calculations)
- Docstrings in code
- CHANGELOG.md (create if needed)

## Code Review Process

Pull requests will be reviewed for:
- Code quality and style
- Test coverage
- Documentation
- Performance impact
- Backward compatibility

Expect feedback within 3-5 business days.

## Questions?

- Open an issue for technical questions
- Email gopal.jamnal@gmail.com for other inquiries

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

Thank you for contributing to make this tool better! 🚀
