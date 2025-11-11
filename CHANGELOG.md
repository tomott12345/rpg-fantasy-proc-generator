# Changelog

All notable changes to the RPG Fantasy Procedural Generator project.

## [v9] - 2025-11-11

### Added
- **OpenAI Integration**: Full integration with OpenAI API for AI-enhanced markdown adventure generation
  - Uses `gpt-4o` model by default (configurable via `ADVENTURE_MODEL` env var)
  - Generates narrative-rich, game-ready D&D adventures from procedural data
  - Proper error handling and API key validation
- **Markdown Adventure Exporter**: Local markdown generation without API requirements
  - Clean, structured markdown output with emoji icons
  - Automatic table formatting for encounters, treasure, and procedural content
  - Supports nested adventure schema with flexible data mapping
- **Schema Mapper**: Converts generator outputs to standardized adventure format
  - Maps settlement, dungeon, and quest data to unified structure
  - Includes pre-built monster encounters, treasure tables, and procedural content
  - Extensible for custom generator formats
- **Complete Workflow Cell**: Single-cell execution for full adventure generation pipeline
  - Step 1: Map outputs to adventure schema
  - Step 2: Generate local markdown
  - Step 3: (Optional) Generate OpenAI-enhanced markdown
- **Environment Variable Support**:
  - `OPENAI_API_KEY`: API key for OpenAI integration
  - `ADVENTURE_MODEL`: Model selection (default: `gpt-4o`)
  - `ADVENTURE_EXPORT_DIR`: Custom export directory (default: `mnt/data/exports`)

### Fixed
- **OpenAI API Integration Issues**:
  - Changed invalid model name from `gpt-5-thinking` to `gpt-4o`
  - Fixed incorrect API method from `responses.create()` to `chat.completions.create()`
  - Removed broken fallback logic with non-existent API methods
  - Improved import error handling with `ImportError` instead of generic `Exception`
- **Variable Scoping in Generators**:
  - Fixed `difficulty_baseline` undefined error in quest generator
  - Added `bind` step to load `difficulty_baseline` from `procgen.global.difficulty_baseline`
  - Corrected lookup path from `meta.difficulty_baseline` to `procgen.global.difficulty_baseline`
- **Export Directory Path Issues**:
  - Changed from absolute path `/mnt/data/exports` to relative path `mnt/data/exports`
  - Ensures compatibility with macOS file system structure
  - Prevents "Read-only file system" errors
- **Code Typos**:
  - Fixed `rint` typo to `print` in workflow cell
  - Commented out example code that was auto-executing before variables were defined

### Improved
- **Markdown Rendering**:
  - Streamlined table generation with better header formatting
  - Enhanced stat block formatting for monsters with clear sections
  - Added emoji icons for visual hierarchy (🗺️, 📜, ⚔️, 🏙️, 🏚️, 👹, 🎲, 💰, 🪤, ✨, 💬, ⚡, 🎯)
  - Consolidated section rendering with `_render_section()` helper function
  - Better handling of nested data structures and missing values
- **Error Messages**:
  - Clear, actionable error messages for missing API keys
  - Explicit instructions for installation and configuration
  - Progress indicators ("Calling OpenAI API...", "✅ Saved Markdown...")
- **Documentation**:
  - Comprehensive usage guide in notebook cells
  - Environment variable documentation
  - Better schema examples with actual structure
  - Quick start guide with code examples

### Changed
- **API Parameters**:
  - Set `temperature` to 0.7 for balanced creativity
  - Set `max_tokens` to 4000 for complete adventures
  - Explicit API key parameter passing to OpenAI client
- **Code Organization**:
  - Separated local export and OpenAI export into distinct cells
  - Added dedicated workflow cell for complete pipeline
  - Better cell documentation with clear section headers

## [v7] - 2025-11-06

### Added
- Modular YAML-based world generation system
- Deep-merge functionality for YAML configuration files
- Procedural generators for settlements, dungeons, and quests
- Dice expression parser with arithmetic support
- Weighted random selection system
- Template interpolation with filters (title, upper, lower)
- Safe expression evaluation for derived values
- Table-based random generation system
- Caching system for procedural tables

### Features
- **World Loading**: Load and merge multiple YAML files from a directory
- **Generators**: Settlement, dungeon, and quest generators with configurable steps
- **Dice Rolling**: Support for expressions like `2d6+3`, `1d4+2`
- **Context System**: Runtime context with variable binding and derivation
- **Output Templates**: String interpolation for formatted output

## Technical Details

### Dependencies
- Python 3.9+
- `pyyaml`: YAML file parsing
- `openai`: OpenAI API integration (optional, for AI-enhanced exports)

### File Structure
```
rpg-fantasy-proc-generator/
├── WorldGen_Starter_v7.ipynb    # Original version
├── WorldGen_Starter_v9.ipynb    # Current version with OpenAI integration
├── mnt/data/
│   ├── world_mod/               # YAML configuration files
│   │   ├── 01_meta.yaml
│   │   ├── 02_tone.yaml
│   │   ├── 16_procgen.yaml     # Generator definitions
│   │   └── ...
│   └── exports/                 # Generated markdown adventures
├── CHANGELOG.md                 # This file
└── OPENAI_INTEGRATION_FIXES.md # Detailed fix documentation
```

### Configuration Files
- `01_meta.yaml`: Project metadata and versioning
- `02_tone.yaml`: World tone and themes
- `16_procgen.yaml`: Generator definitions and procedural tables
  - Global settings (difficulty_baseline, encounter_frequency)
  - Weights for regions, biomes, climates, etc.
  - Dice expressions for dynamic values
  - Generator step definitions

### Generator Steps
Supported step types:
- `choose`: Select from weighted options
- `roll`: Roll dice expressions
- `pick_n`: Select N random items from a list
- `derive`: Calculate values using expressions
- `table`: Roll on procedural tables
- `bind`: Bind values or lookup from world data
- `output_template`: Generate formatted output

## Migration Guide

### From v7 to v9

**No Breaking Changes**: v9 is fully backward compatible with v7.

**New Features Available**:
1. Run your existing generators as before
2. Use `map_to_standard_schema(outputs)` to convert to adventure format
3. Use `save_markdown()` for local export
4. (Optional) Use `call_openai_and_save()` for AI-enhanced export

**Recommended Updates**:
- Update `16_procgen.yaml` to include `difficulty_baseline` lookup in quest generator
- Set `OPENAI_API_KEY` environment variable if using AI features
- Update export directory path if using custom locations

## Known Issues

None currently reported.

## Future Enhancements

- [ ] Additional generator types (NPCs, factions, regions)
- [ ] More procedural table types (magic items, plot hooks)
- [ ] PDF export support
- [ ] Web-based UI for generator configuration
- [ ] Integration with VTT platforms (Roll20, Foundry VTT)
- [ ] Support for other RPG systems (Pathfinder, OSR, etc.)

## Credits

**Author**: Thomas Ott  
**Project**: Etheras World Generator  
**Version**: 1.1  
**Date**: November 2025

## License

[Specify your license here]

## Support

For issues, questions, or contributions, please refer to the project repository.
