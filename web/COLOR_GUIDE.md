# Dashboard Color Customization Guide

All colors are defined in `src/App.css`. Here's how to customize them:

## Light Mode Colors

Edit these in the main CSS (around line 1-500):

```css
/* Background & Cards */
background: #f3f4f6;           /* Page background */
background: white;             /* Card backgrounds */
border: 1px solid #e5e7eb;    /* Borders */

/* Text */
color: #111827;                /* Main text */
color: #666;                   /* Secondary text */
color: #999;                   /* Muted text */

/* Accent Colors */
background: #667eea;           /* Primary buttons/highlights */
color: #667eea;                /* Links */
background: #f3f4f6;           /* Hover states */

/* Message Colors */
color: #5865F2;                /* Author names (default) */
color: #94a3b8;                /* Timestamps */
color: #10b981;                /* Channel names */
```

## Dark Mode Colors

Edit these in `.dark-mode` section (around line 596-792):

```css
/* Background & Cards */
background: #2c2d32;           /* Page background */
background: #323339;           /* Card backgrounds */
background: #2c2d32;           /* Interactive elements */
border-color: #2c2d32;         /* Borders */

/* Text */
color: #cdd6f4;                /* Main text */
color: #bac2de;                /* Secondary text */
color: #9399b2;                /* Muted text */

/* Accent Colors */
background: #89b4fa;           /* Primary buttons/highlights */
color: #89dceb;                /* Links */
color: #94e2d5;                /* Channel names */

/* Message Colors */
color: #89b4fa;                /* Author names (default) */
color: #7f849c;                /* Timestamps */
color: #a6e3a1;                /* Success/green */
color: #f38ba8;                /* Error/red */
```

## Quick Color Swap Examples

### Change Accent Color (Light Mode)
Find all instances of `#667eea` and replace with your color:
- `#667eea` → `#ff6b6b` (Red)
- `#667eea` → `#4ecdc4` (Teal)
- `#667eea` → `#a29bfe` (Purple)

### Change Accent Color (Dark Mode)
Find all instances of `#89b4fa` and replace with your color:
- `#89b4fa` → `#f38ba8` (Pink)
- `#89b4fa` → `#fab387` (Orange)
- `#89b4fa` → `#a6e3a1` (Green)

### Change Background (Dark Mode)
```css
.app.dark-mode {
  background: #0d1117;  /* GitHub dark */
}

.dark-mode .header,
.dark-mode .sidebar,
.dark-mode .main-content {
  background: #161b22;  /* Slightly lighter */
}
```

## Pre-made Color Schemes

### Discord Theme
```css
/* Light Mode */
background: #5865F2;  /* Discord Blurple */

/* Dark Mode */
background: #2b2d31;  /* Discord Dark */
```

### Dracula Theme
```css
background: #282a36;  /* Background */
background: #44475a;  /* Current Line */
color: #f8f8f2;       /* Foreground */
color: #bd93f9;       /* Purple */
color: #ff79c6;       /* Pink */
color: #50fa7b;       /* Green */
```

### Nord Theme
```css
background: #2e3440;  /* Polar Night */
background: #3b4252;  /* Lighter */
color: #eceff4;       /* Snow Storm */
color: #88c0d0;       /* Frost */
color: #81a1c1;       /* Frost 2 */
```

## After Making Changes

1. Save `App.css`
2. Run `npm run build` in the web folder
3. Commit and push to deploy

The changes will apply immediately after deployment!
