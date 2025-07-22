from flask import Flask, render_template, request, jsonify, send_file, session
from flask_cors import CORS
from flask_mail import Mail, Message
import os
import uuid
import json
import sqlite3
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
from reportlab.lib.colors import HexColor
import io
import secrets
from functools import wraps
import hashlib

app = Flask(__name__)
CORS(app)
app.secret_key = os.environ.get('SECRET_KEY', secrets.token_hex(32))

# Configuration
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_DEFAULT_SENDER', 'noreply@reflexionmirror.com')

mail = Mail(app)

# Configure folders
UPLOAD_FOLDER = 'reflections'
DATABASE_PATH = 'reflexion_mirror.db'
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Enhanced archetypes with visuals and quotes
ARCHETYPES = {
    "phoenix": {
        "description": "Rising from ashes, transformed by fire",
        "symbol": "🔥",
        "quote": "What is to give light must endure burning. - Viktor Frankl",
        "color": "#ff6b6b"
    },
    "alchemist": {
        "description": "Transmuting pain into wisdom",
        "symbol": "⚗️",
        "quote": "One does not become enlightened by imagining figures of light, but by making the darkness conscious. - Carl Jung",
        "color": "#4ecdc4"
    },
    "warrior": {
        "description": "Forged in battle, tempered by trials",
        "symbol": "⚔️",
        "quote": "The wound is the place where the Light enters you. - Rumi",
        "color": "#ff9f43"
    },
    "sage": {
        "description": "Seeking truth through suffering",
        "symbol": "🦉",
        "quote": "The only true wisdom is in knowing you know nothing. - Socrates",
        "color": "#a8e6cf"
    },
    "wanderer": {
        "description": "Lost to find, broken to become whole",
        "symbol": "🧭",
        "quote": "Not all those who wander are lost. - J.R.R. Tolkien",
        "color": "#c7ceea"
    },
    "architect": {
        "description": "Building from ruins, designing destiny",
        "symbol": "🏛️",
        "quote": "In the depth of winter, I finally learned that there was in me an invincible summer. - Albert Camus",
        "color": "#b2bec3"
    },
    "mystic": {
        "description": "Embracing the void to find the light",
        "symbol": "🔮",
        "quote": "The cave you fear to enter holds the treasure you seek. - Joseph Campbell",
        "color": "#dfe6e9"
    },
    "rebel": {
        "description": "Destroying to create, refusing to conform",
        "symbol": "⚡",
        "quote": "You must be ready to burn yourself in your own flame; how could you rise anew if you have not first become ashes? - Nietzsche",
        "color": "#fd79a8"
    }
}

# Input field guidance
FIELD_GUIDANCE = {
    "collapse": {
        "prompts": [
            "What shattered your previous understanding of self?",
            "Describe the moment everything you knew fell apart.",
            "What belief system or identity crumbled?",
            "When did the ground beneath you disappear?"
        ],
        "examples": [
            "The day I realized my entire career was built on others' expectations",
            "When chronic illness forced me to abandon my identity as 'the strong one'",
            "After the betrayal that made me question everything I believed about trust",
            "The moment I understood my perfectionism was destroying me from within"
        ]
    },
    "build": {
        "prompts": [
            "What emerged from the rubble of your former self?",
            "Which strengths crystallized in the crucible?",
            "What new capacities did suffering reveal?",
            "How did you reconstruct meaning from chaos?"
        ],
        "examples": [
            "I learned to find power in vulnerability and authentic connection",
            "Developed an unshakeable inner compass independent of external validation",
            "Built resilience through radical acceptance of uncertainty",
            "Created art from pain, transforming wounds into wisdom"
        ]
    },
    "now": {
        "prompts": [
            "Who stands here now, transformed?",
            "What is your essential nature after the journey?",
            "How do you move through the world differently?",
            "What truth do you embody?"
        ],
        "examples": [
            "A guide who helps others navigate their own dark nights",
            "Someone who dances with chaos rather than fearing it",
            "A bridge between worlds, holding space for transformation",
            "An authentic being who no longer wears masks"
        ]
    }
}

# Database initialization
def init_db():
    """Initialize SQLite database for archive system"""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS reflections
                 (id TEXT PRIMARY KEY,
                  user_id TEXT,
                  collapse TEXT,
                  build TEXT,
                  now TEXT,
                  archetype TEXT,
                  narrative TEXT,
                  created_at TIMESTAMP,
                  email TEXT,
                  is_public BOOLEAN DEFAULT 0)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS chat_sessions
                 (id TEXT PRIMARY KEY,
                  user_id TEXT,
                  messages TEXT,
                  created_at TIMESTAMP,
                  updated_at TIMESTAMP)''')
    
    conn.commit()
    conn.close()

init_db()

# Helper functions
def get_user_id():
    """Get or create user session ID"""
    if 'user_id' not in session:
        session['user_id'] = str(uuid.uuid4())
    return session['user_id']

def save_reflection(reflection_data):
    """Save reflection to database"""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    c.execute('''INSERT INTO reflections 
                 (id, user_id, collapse, build, now, archetype, narrative, created_at, email, is_public)
                 VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
              (reflection_data['id'],
               reflection_data['user_id'],
               reflection_data['collapse'],
               reflection_data['build'],
               reflection_data['now'],
               reflection_data['archetype'],
               reflection_data['narrative'],
               reflection_data['created_at'],
               reflection_data.get('email', ''),
               reflection_data.get('is_public', False)))
    
    conn.commit()
    conn.close()

def generate_reflexion_dna(collapse, build, now, archetype):
    """Generate a Reflexion DNA - symbolic fingerprint of transformation"""
    
    # Extract core themes
    collapse_root = extract_core_theme(collapse, ['control', 'identity', 'trust', 'purpose', 'belonging', 'certainty'])
    emergent_trait = extract_core_theme(build, ['resilience', 'wisdom', 'compassion', 'strength', 'clarity', 'freedom'])
    final_state = extract_core_theme(now, ['authentic', 'integrated', 'empowered', 'aligned', 'whole', 'awakened'])
    
    # Generate theme chain
    theme_chain = []
    for text in [collapse, build, now]:
        themes = extract_themes(text)
        if themes:
            theme_chain.append(themes[0])
    
    # Create DNA structure
    dna = {
        "collapse_root": collapse_root,
        "emergent_trait": emergent_trait,
        "final_state": final_state,
        "archetype": archetype if archetype else "wanderer",
        "theme_chain": theme_chain,
        "transformation_hash": generate_transformation_hash(collapse, build, now)
    }
    
    return dna

def extract_core_theme(text, themes):
    """Extract the most relevant theme from text"""
    text_lower = text.lower()
    for theme in themes:
        if theme in text_lower:
            return theme
    return themes[0]  # Default to first theme

def extract_themes(text):
    """Extract key themes from text"""
    # Simple theme extraction - can be enhanced with NLP
    themes = []
    theme_words = {
        'loss': ['lost', 'gone', 'ended', 'died'],
        'betrayal': ['betrayed', 'trust', 'lied', 'deceived'],
        'failure': ['failed', 'mistake', 'wrong', 'error'],
        'awakening': ['realized', 'understood', 'saw', 'discovered'],
        'rebuilding': ['built', 'created', 'started', 'began'],
        'transformation': ['changed', 'became', 'transformed', 'evolved'],
        'freedom': ['free', 'liberated', 'released', 'escaped'],
        'integration': ['whole', 'complete', 'integrated', 'unified']
    }
    
    text_lower = text.lower()
    for theme, keywords in theme_words.items():
        if any(keyword in text_lower for keyword in keywords):
            themes.append(theme)
    
    return themes[:3]  # Return top 3 themes

def generate_transformation_hash(collapse, build, now):
    """Generate a unique hash for the transformation journey"""
    combined = f"{collapse[:50]}{build[:50]}{now[:50]}"
    return hashlib.sha256(combined.encode()).hexdigest()[:12]

def generate_share_code(reflection_id, archetype, timestamp):
    """Generate a mystical share code/sigil"""
    # Create components
    arch_prefix = archetype[:3].upper() if archetype else "WND"
    time_component = str(int(timestamp.timestamp()))[-4:]
    id_component = reflection_id[:4].upper()
    
    # Generate sigil pattern
    sigil = f"{arch_prefix}-{time_component}-{id_component}"
    
    return sigil

def get_user_reflections(user_id):
    """Get all reflections for a user"""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    c.execute('''SELECT * FROM reflections 
                 WHERE user_id = ? 
                 ORDER BY created_at DESC''', (user_id,))
    
    reflections = []
    for row in c.fetchall():
        reflections.append({
            'id': row[0],
            'collapse': row[2],
            'build': row[3],
            'now': row[4],
            'archetype': row[5],
            'narrative': row[6],
            'created_at': row[7],
            'email': row[8],
            'is_public': row[9]
        })
    
    conn.close()
    return reflections

def generate_narrative(collapse: str, build: str, now: str, archetype: str) -> str:
    """Construct a transformation narrative from the user inputs.

    Given the three phases of the transformation journey—collapse, build, and now—
    this helper function weaves them into a cohesive narrative.  It uses
    section markers to delineate the phases and draws on the selected archetype
    (if provided) to offer additional context and symbolism.  The narrative is
    returned as a plain string with line breaks separating the sections.

    Args:
        collapse: Description of what was lost or dissolved.
        build: Description of the rebuilding or integration phase.
        now: Description of the current state after transformation.
        archetype: Optional archetype key from the ARCHETYPES dictionary.

    Returns:
        A multi‑line string summarizing the user's transformation journey.
    """
    sections = []

    # Collapse section
    sections.append("【 COLLAPSE 】\n" +
                    "In the depths of dissolution, you faced the void:\n" +
                    collapse.strip())

    # Build/compression section
    sections.append("\n【 COMPRESSION 】\n" +
                    "From the fragments, you forged something new:\n" +
                    build.strip())

    # Convergence section
    sections.append("\n【 CONVERGENCE 】\n" +
                    "Now, you stand transformed:\n" +
                    now.strip())

    # Archetype section, if provided
    if archetype:
        arch_data = ARCHETYPES.get(archetype.lower())
        if arch_data:
            sections.append(
                f"\n【 ARCHETYPE 】\nYou embody the {archetype.title()}: {arch_data['description']}\n\n"
                f"{arch_data['quote']}"
            )
        else:
            sections.append(
                "\n【 ARCHETYPE 】\nYour archetype is still crystallizing in the cosmic forge"
            )

    return "\n\n".join(sections)

@app.route('/')
def index():
    """Render the main input form using the correct template name.

    The application uses custom HTML templates with the `_html.html` suffix.  When
    the new templates were uploaded, the default `render_template` calls still
    referenced the old names (e.g. `form.html`).  To ensure Flask loads the
    correct files from the `templates` directory, update this route to use
    `reflexion_form_html.html` instead.  Additional context (e.g. archetypes
    and guidance text) is passed to the template for rendering.
    """
    return render_template(
        'reflexion_form_html.html',
        archetypes=ARCHETYPES,
        field_guidance=FIELD_GUIDANCE
    )

@app.route('/mirror', methods=['POST'])
def mirror():
    user_id = get_user_id()
    collapse = request.form.get('collapse', '').strip()
    build = request.form.get('build', '').strip()
    now = request.form.get('now', '').strip()
    archetype = request.form.get('archetype', '').strip().lower()
    email = request.form.get('email', '').strip()
    is_public = request.form.get('is_public', 'off') == 'on'
    
    # Generate narrative
    narrative = generate_narrative(collapse, build, now, archetype)
    
    # Generate Reflexion DNA
    reflexion_dna = generate_reflexion_dna(collapse, build, now, archetype)
    
    # Save to database
    reflection_id = str(uuid.uuid4())[:8]
    created_at = datetime.now()
    
    reflection_data = {
        'id': reflection_id,
        'user_id': user_id,
        'collapse': collapse,
        'build': build,
        'now': now,
        'archetype': archetype,
        'narrative': narrative,
        'created_at': created_at,
        'email': email,
        'is_public': is_public
    }
    save_reflection(reflection_data)
    
    # Generate share code
    share_code = generate_share_code(reflection_id, archetype, created_at)
    
    # === COLLAPSE ARCHIVE LOGGING ===
    # Create archive directory
    log_dir = "Collapse_Archive"
    os.makedirs(log_dir, exist_ok=True)
    
    # Generate entry ID based on existing files
    existing_files = [f for f in os.listdir(log_dir) if f.endswith('.json')]
    entry_number = len(existing_files) + 1
    entry_id = f"entry_{entry_number:03d}"
    
    # Create compressed summaries with symbolic interpretation
    compressed_summary = generate_compressed_summary(collapse, build, now, archetype)
    
    # Prepare log data with DNA
    log_data = {
        "id": entry_id,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "reflection_id": reflection_id,
        "user_id": user_id,
        "collapse": collapse,
        "build": build,
        "now": now,
        "archetype": archetype if archetype else "unassigned",
        "compressed_summary": compressed_summary,
        "reflexion_dna": reflexion_dna,
        "share_code": share_code,
        "is_public": is_public,
        "metadata": {
            "word_count": {
                "collapse": len(collapse.split()),
                "build": len(build.split()),
                "now": len(now.split())
            },
            "archetype_data": ARCHETYPES.get(archetype, {}) if archetype else None,
            "email_sent": bool(email),
            "processing_timestamp": datetime.utcnow().isoformat() + "Z"
        }
    }
    
    # Write to JSON file
    log_filepath = os.path.join(log_dir, f"collapse_{entry_id}.json")
    try:
        with open(log_filepath, "w", encoding='utf-8') as f:
            json.dump(log_data, f, indent=4, ensure_ascii=False)
        print(f"Logged collapse entry: {log_filepath}")
    except Exception as e:
        print(f"Error logging collapse entry: {e}")
    
    # Send email if requested
    if email:
        try:
            send_reflection_email(email, narrative, reflection_id)
        except Exception as e:
            print(f"Email error: {e}")
    
    return render_template(
        'reflexion_mirror_html.html',
        reflection=narrative,
        reflection_id=reflection_id,
        collapse=collapse,
        build=build,
        now=now,
        archetype=archetype,
        archetype_data=ARCHETYPES.get(archetype, None),
        reflexion_dna=reflexion_dna,
        share_code=share_code,
        is_public=is_public
    )

@app.route('/archive')
def archive():
    """Display the user's reflection archive using the updated template name."""
    user_id = get_user_id()
    reflections = get_user_reflections(user_id)
    return render_template(
        'reflexion_archive_html.html',
        reflections=reflections,
        archetypes=ARCHETYPES
    )

@app.route('/explore')
def explore():
    """Public exploration of shared reflections using the updated template name."""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    # Get public reflections
    c.execute('''SELECT * FROM reflections 
                 WHERE is_public = 1 
                 ORDER BY created_at DESC 
                 LIMIT 50''')
    
    public_reflections = []
    for row in c.fetchall():
        public_reflections.append({
            'id': row[0],
            'collapse': row[2][:200] + '...' if len(row[2]) > 200 else row[2],
            'build': row[3][:200] + '...' if len(row[3]) > 200 else row[3],
            'now': row[4][:200] + '...' if len(row[4]) > 200 else row[4],
            'archetype': row[5],
            'created_at': row[7]
        })
    
    conn.close()
    return render_template(
        'reflexion_explore_html.html',
        reflections=public_reflections,
        archetypes=ARCHETYPES
    )

@app.route('/reflection/<reflection_id>')
def view_reflection(reflection_id):
    """View a specific public reflection"""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    c.execute('SELECT * FROM reflections WHERE id = ? AND is_public = 1', (reflection_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        reflection = {
            'id': row[0],
            'collapse': row[2],
            'build': row[3],
            'now': row[4],
            'archetype': row[5],
            'narrative': row[6],
            'created_at': row[7]
        }
        return render_template('public_reflection.html', 
                             reflection=reflection,
                             archetype_data=ARCHETYPES.get(row[5], None))
    
    return "Reflection not found or not public", 404

@app.route('/api/reflection/<reflection_id>')
def get_reflection(reflection_id):
    """Get a specific reflection"""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    c.execute('SELECT * FROM reflections WHERE id = ?', (reflection_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        return jsonify({
            'id': row[0],
            'collapse': row[2],
            'build': row[3],
            'now': row[4],
            'archetype': row[5],
            'narrative': row[6],
            'created_at': row[7].isoformat() if row[7] else None
        })
    return jsonify({'error': 'Reflection not found'}), 404

@app.route('/export/<format>/<reflection_id>')
def export_reflection(format, reflection_id):
    """Export reflection in various formats"""
    # Get reflection data
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    c.execute('SELECT * FROM reflections WHERE id = ?', (reflection_id,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        return jsonify({'error': 'Reflection not found'}), 404
    
    narrative = row[6]
    
    if format == 'txt':
        # Plain text export
        buffer = io.BytesIO()
        buffer.write(narrative.encode('utf-8'))
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'reflexion_{reflection_id}.txt',
            mimetype='text/plain'
        )
    
    elif format == 'md':
        # Markdown export.
        # Compute the processed narrative outside the f-string to avoid using
        # backslashes inside the expression.  f-strings forbid backslashes in
        # expressions, so any replacement that inserts a newline must be done
        # beforehand.
        processed_narrative = narrative.replace('【', '## 【').replace('】', '】\n')
        md_content = f"""# Reflexion Mirror - Personal Transformation Narrative

Generated: {row[7]}  
ID: {reflection_id}

---

    {processed_narrative}

---

*Generated by Reflexion Mirror - A tool for symbolic identity reflection*
"""
        buffer = io.BytesIO()
        buffer.write(md_content.encode('utf-8'))
        buffer.seek(0)
        
        return send_file(
            buffer,
            as_attachment=True,
            download_name=f'reflexion_{reflection_id}.md',
            mimetype='text/markdown'
        )
    
    elif format == 'pdf':
        # Use existing PDF generation
        return generate_pdf_from_data({
            'collapse': row[2],
            'build': row[3],
            'now': row[4],
            'archetype': row[5]
        })

@app.route('/chat')
def chat():
    """Claude-powered chat interface"""
    # Render the chat interface using the updated template filename
    return render_template('reflexion_chat_html.html')

@app.route('/api/chat', methods=['POST'])
def api_chat():
    """Handle chat messages with recursive symbolic prompts"""
    user_id = get_user_id()
    message = request.json.get('message', '')
    session_id = request.json.get('session_id', str(uuid.uuid4()))
    
    # This would integrate with Claude API
    # For now, return a placeholder response
    response = generate_chat_response(message, session_id)
    
    return jsonify({
        'response': response,
        'session_id': session_id
    })

def generate_chat_response(message, session_id):
    """Generate symbolic chat response (placeholder for Claude integration)"""
    # This is where you'd integrate Claude API
    # For now, return themed responses
    
    prompts = [
        "Tell me more about what this experience revealed to you.",
        "What patterns do you notice in your transformation?",
        "How does this connect to your deeper mythology?",
        "What would your transformed self tell your past self?",
        "Where do you feel this journey leading you next?"
    ]
    
    import random
    return random.choice(prompts)

def generate_compressed_summary(collapse, build, now, archetype):
    """Generate symbolic compressed interpretations of the transformation journey"""
    
    # Extract key themes and patterns
    collapse_keywords = extract_keywords(collapse)
    build_keywords = extract_keywords(build)
    now_keywords = extract_keywords(now)
    
    # Generate compressed symbolic interpretations
    compressed = {
        "Collapse": f"The dissolution began when {collapse_keywords} shattered the illusion of {get_lost_element(collapse)}",
        "Compression": f"Through {build_keywords}, the fragments crystallized into {get_emergent_quality(build)}",
        "Convergence": f"Now standing as {now_keywords}, embodying the truth of {get_essential_nature(now)}"
    }
    
    # Add archetype-specific compression if available
    if archetype and archetype in ARCHETYPES:
        arch_data = ARCHETYPES[archetype]
        compressed["Archetypal_Pattern"] = f"Walking the {archetype}'s path: {arch_data['description']}"
    
    return compressed

def extract_keywords(text):
    """Extract key thematic words from text"""
    # Simple keyword extraction - can be enhanced with NLP
    words = text.lower().split()
    # Filter common words
    stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by', 'from', 'was', 'were', 'been', 'be', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could', 'should', 'may', 'might', 'must', 'can', 'is', 'are', 'am', 'it', 'i', 'you', 'he', 'she', 'they', 'we', 'me', 'him', 'her', 'them', 'my', 'your', 'his', 'its', 'our', 'their'}
    keywords = [w for w in words if w not in stop_words and len(w) > 3]
    return ' '.join(keywords[:3]) if keywords else 'the unnamed'

def get_lost_element(collapse_text):
    """Extract what was lost in the collapse"""
    patterns = ['identity', 'certainty', 'control', 'belonging', 'purpose', 'self']
    for pattern in patterns:
        if pattern in collapse_text.lower():
            return pattern
    return 'stability'

def get_emergent_quality(build_text):
    """Extract what emerged from the building"""
    patterns = ['strength', 'wisdom', 'resilience', 'understanding', 'compassion', 'power', 'clarity']
    for pattern in patterns:
        if pattern in build_text.lower():
            return pattern
    return 'new foundations'

def get_essential_nature(now_text):
    """Extract the essential nature of current state"""
    patterns = ['authenticity', 'wholeness', 'integration', 'transformation', 'truth', 'freedom']
    for pattern in patterns:
        if pattern in now_text.lower():
            return pattern
    return 'irreducible essence'

@app.route('/collapse-archive')
def collapse_archive():
    """View the collapse archive dashboard"""
    log_dir = "Collapse_Archive"
    entries = []
    
    if os.path.exists(log_dir):
        # Read all JSON files
        for filename in sorted(os.listdir(log_dir)):
            if filename.endswith('.json'):
                filepath = os.path.join(log_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        entry = json.load(f)
                        entries.append(entry)
                except Exception as e:
                    print(f"Error reading {filename}: {e}")
    
    # Calculate statistics
    stats = {
        'total_entries': len(entries),
        'archetypes': {},
        'avg_word_counts': {'collapse': 0, 'build': 0, 'now': 0},
        'recent_entries': entries[-10:][::-1] if entries else []
    }
    
    if entries:
        # Count archetypes
        for entry in entries:
            arch = entry.get('archetype', 'unassigned')
            stats['archetypes'][arch] = stats['archetypes'].get(arch, 0) + 1
        
        # Calculate average word counts
        for field in ['collapse', 'build', 'now']:
            total_words = sum(entry.get('metadata', {}).get('word_count', {}).get(field, 0) for entry in entries)
            stats['avg_word_counts'][field] = round(total_words / len(entries), 1)
    
    # Render the collapse archive dashboard using the updated template filename
    return render_template(
        'collapse_dashboard_html.html',
        entries=entries,
        stats=stats
    )

@app.route('/api/collapse-archive/<entry_id>')
def get_collapse_entry(entry_id):
    """Get a specific collapse archive entry"""
    log_dir = "Collapse_Archive"
    filepath = os.path.join(log_dir, f"collapse_{entry_id}.json")
    
    if os.path.exists(filepath):
        with open(filepath, 'r', encoding='utf-8') as f:
            return jsonify(json.load(f))
    
    return jsonify({'error': 'Entry not found'}), 404

@app.route('/api/collapse-archive/export')
def export_collapse_archive():
    """Export all collapse archive entries as a single JSON file"""
    log_dir = "Collapse_Archive"
    all_entries = []
    
    if os.path.exists(log_dir):
        for filename in sorted(os.listdir(log_dir)):
            if filename.endswith('.json'):
                filepath = os.path.join(log_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        all_entries.append(json.load(f))
                except Exception as e:
                    print(f"Error reading {filename}: {e}")
    
    # Create export data
    export_data = {
        'export_timestamp': datetime.utcnow().isoformat() + 'Z',
        'total_entries': len(all_entries),
        'entries': all_entries
    }
    
    # Convert to JSON and send as file
    buffer = io.BytesIO()
    buffer.write(json.dumps(export_data, indent=2).encode('utf-8'))
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'collapse_archive_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
        mimetype='application/json'
    )

# Admin routes (basic auth - enhance for production)
def check_admin_auth():
    """Simple admin authentication check"""
    auth = request.authorization
    admin_username = os.environ.get('ADMIN_USERNAME', 'admin')
    admin_password = os.environ.get('ADMIN_PASSWORD', 'reflexion2024')
    
    if not auth or auth.username != admin_username or auth.password != admin_password:
        return False
    return True

def require_admin(f):
    """Admin authentication decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not check_admin_auth():
            return 'Authentication required', 401, {'WWW-Authenticate': 'Basic realm="Admin"'}
        return f(*args, **kwargs)
    return decorated_function

@app.route('/admin')
@require_admin
def admin_dashboard():
    """Admin dashboard with analytics"""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    # Get statistics
    stats = {}
    
    # Total users
    c.execute('SELECT COUNT(DISTINCT user_id) FROM reflections')
    stats['total_users'] = c.fetchone()[0]
    
    # Total reflections
    c.execute('SELECT COUNT(*) FROM reflections')
    stats['total_reflections'] = c.fetchone()[0]
    
    # Public reflections
    c.execute('SELECT COUNT(*) FROM reflections WHERE is_public = 1')
    stats['public_reflections'] = c.fetchone()[0]
    
    # Growth over time (last 30 days)
    c.execute('''
        SELECT DATE(created_at) as date, COUNT(*) as count 
        FROM reflections 
        WHERE created_at > datetime('now', '-30 days')
        GROUP BY DATE(created_at)
        ORDER BY date
    ''')
    growth_data = c.fetchall()
    stats['growth_chart'] = [{'date': row[0], 'count': row[1]} for row in growth_data]
    
    # Popular archetypes
    c.execute('''
        SELECT archetype, COUNT(*) as count 
        FROM reflections 
        WHERE archetype != ''
        GROUP BY archetype 
        ORDER BY count DESC
    ''')
    archetype_data = c.fetchall()
    stats['popular_archetypes'] = [{'archetype': row[0], 'count': row[1]} for row in archetype_data]
    
    # Recent reflections
    c.execute('''
        SELECT id, user_id, archetype, created_at, is_public 
        FROM reflections 
        ORDER BY created_at DESC 
        LIMIT 20
    ''')
    recent = c.fetchall()
    stats['recent_reflections'] = [{
        'id': row[0],
        'user_id': row[1][:8],
        'archetype': row[2],
        'created_at': row[3],
        'is_public': row[4]
    } for row in recent]
    
    conn.close()
    
    # Render the admin dashboard using the updated template filename
    return render_template(
        'admin_dashboard_html.html',
        stats=stats,
        archetypes=ARCHETYPES
    )

@app.route('/api/admin/export-all')
@require_admin
def admin_export_all():
    """Export all data for admin"""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    # Export all tables
    export_data = {
        'export_timestamp': datetime.utcnow().isoformat() + 'Z',
        'tables': {}
    }
    
    # Export reflections
    c.execute("SELECT * FROM reflections")
    columns = [description[0] for description in c.description]
    reflections = []
    for row in c.fetchall():
        reflections.append(dict(zip(columns, row)))
    export_data['tables']['reflections'] = reflections
    
    # Export chat sessions
    c.execute("SELECT * FROM chat_sessions")
    columns = [description[0] for description in c.description]
    chat_sessions = []
    for row in c.fetchall():
        chat_sessions.append(dict(zip(columns, row)))
    export_data['tables']['chat_sessions'] = chat_sessions
    
    conn.close()
    
    # Add collapse archive data
    log_dir = "Collapse_Archive"
    collapse_entries = []
    if os.path.exists(log_dir):
        for filename in sorted(os.listdir(log_dir)):
            if filename.endswith('.json'):
                filepath = os.path.join(log_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        collapse_entries.append(json.load(f))
                except:
                    pass
    
    export_data['collapse_archive'] = collapse_entries
    
    # Create export file
    buffer = io.BytesIO()
    buffer.write(json.dumps(export_data, indent=2, default=str).encode('utf-8'))
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'reflexion_mirror_full_export_{datetime.now().strftime("%Y%m%d_%H%M%S")}.json',
        mimetype='application/json'
    )

@app.route('/api/reflexion-dna/<reflection_id>')
def get_reflexion_dna(reflection_id):
    """Get Reflexion DNA for a specific reflection"""
    conn = sqlite3.connect(DATABASE_PATH)
    c = conn.cursor()
    
    c.execute('SELECT collapse, build, now, archetype FROM reflections WHERE id = ?', (reflection_id,))
    row = c.fetchone()
    conn.close()
    
    if row:
        dna = generate_reflexion_dna(row[0], row[1], row[2], row[3])
        return jsonify(dna)
    
    return jsonify({'error': 'Reflection not found'}), 404
    """Enhanced narrative generation with archetype integration"""
    sections = []
    
    # Opening
    sections.append("═══ REFLEXION ═══\n")
    
    # Add archetype header if selected
    if archetype and archetype in ARCHETYPES:
        arch_data = ARCHETYPES[archetype]
        sections.append(f"{arch_data['symbol']} The {archetype.title()}'s Journey {arch_data['symbol']}\n")
    
    # Collapse phase
    sections.append("【 COLLAPSE 】")
    sections.append(f"In the depths of dissolution, you faced the void:")
    sections.append(f"» {collapse}")
    sections.append(f"This was your katabasis—the necessary descent.")
    sections.append("")
    
    # Compression phase
    sections.append("【 COMPRESSION 】")
    sections.append(f"From the fragments, you forged something new:")
    sections.append(f"» {build}")
    sections.append(f"In the crucible of transformation, you discovered resilience.")
    sections.append("")
    
    # Convergence phase
    sections.append("【 CONVERGENCE 】")
    sections.append(f"Now, you stand transformed:")
    sections.append(f"» {now}")
    sections.append(f"You have become the author of your own mythology.")
    sections.append("")
    
    # Enhanced archetype integration
    sections.append("【 ARCHETYPE 】")
    if archetype and archetype in ARCHETYPES:
        arch_data = ARCHETYPES[archetype]
        sections.append(f"You embody the {archetype.title()}: {arch_data['description']}")
        sections.append(f"\n「 {arch_data['quote']} 」")
    elif archetype:
        sections.append(f"You walk the path of the {archetype.title()}")
    else:
        sections.append("Your archetype is still crystallizing in the cosmic forge")
    sections.append("")
    
    # Synthesis
    sections.append("【 SYNTHESIS 】")
    sections.append("Your journey maps the eternal pattern:")
    sections.append("Dissolution → Crystallization → Emergence")
    sections.append("What was broken has become the foundation.")
    sections.append("What was lost has become the compass.")
    sections.append("What remains is irreducibly you.")
    
    return "\n".join(sections)

def send_reflection_email(email, narrative, reflection_id):
    """Send reflection via email"""
    msg = Message(
        'Your Reflexion Mirror - Personal Transformation Narrative',
        recipients=[email]
    )
    
    msg.body = f"""Your personal transformation narrative has been generated.

{narrative}

---
Reflection ID: {reflection_id}
View online: {request.host_url}reflection/{reflection_id}

Thank you for using Reflexion Mirror.
"""
    
    msg.html = f"""
    <html>
    <body style="font-family: 'Georgia', serif; color: #333; line-height: 1.6; max-width: 600px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #667eea;">Your Reflexion Mirror</h2>
        <p>Your personal transformation narrative has been generated.</p>
        
        <div style="background: #f5f5f5; padding: 20px; border-radius: 10px; margin: 20px 0;">
            <pre style="white-space: pre-wrap; font-family: 'Courier New', monospace;">{narrative}</pre>
        </div>
        
        <p style="color: #666; font-size: 0.9em;">
            Reflection ID: {reflection_id}<br>
            <a href="{request.host_url}reflection/{reflection_id}" style="color: #667eea;">View online</a>
        </p>
        
        <hr style="border: none; border-top: 1px solid #eee; margin: 30px 0;">
        
        <p style="color: #999; font-size: 0.8em; text-align: center;">
            Reflexion Mirror - A tool for symbolic identity reflection
        </p>
    </body>
    </html>
    """
    
    mail.send(msg)

@app.route('/generate_pdf', methods=['POST'])
def generate_pdf():
    """Enhanced PDF generation"""
    data = request.json
    return generate_pdf_from_data(data)

def generate_pdf_from_data(data):
    """Generate PDF from reflection data"""
    collapse = data.get('collapse', '')
    build = data.get('build', '')
    now = data.get('now', '')
    archetype = data.get('archetype', '')
    
    # Create PDF in memory
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter,
                          rightMargin=72, leftMargin=72,
                          topMargin=72, bottomMargin=18)
    
    elements = []
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Title'],
        fontSize=24,
        textColor=HexColor('#2c3e50'),
        spaceAfter=30,
        alignment=1
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading1'],
        fontSize=16,
        textColor=HexColor('#34495e'),
        spaceAfter=12,
        spaceBefore=20
    )
    
    body_style = ParagraphStyle(
        'CustomBody',
        parent=styles['BodyText'],
        fontSize=12,
        leading=16,
        textColor=HexColor('#2c3e50'),
        spaceAfter=12
    )
    
    quote_style = ParagraphStyle(
        'Quote',
        parent=styles['Italic'],
        fontSize=14,
        leftIndent=20,
        rightIndent=20,
        textColor=HexColor('#7f8c8d'),
        spaceAfter=16,
        leading=18
    )
    
    # Add content
    elements.append(Paragraph("REFLEXION MIRROR", title_style))
    
    # Add archetype symbol if exists
    if archetype and archetype in ARCHETYPES:
        arch_data = ARCHETYPES[archetype]
        elements.append(Paragraph(f"{arch_data['symbol']} The {archetype.title()}'s Journey", body_style))
    
    elements.append(Paragraph("A Symbolic Identity Reflection", body_style))
    elements.append(Spacer(1, 0.5*inch))
    
    # Date
    elements.append(Paragraph(f"Generated: {datetime.now().strftime('%B %d, %Y')}", body_style))
    elements.append(Spacer(1, 0.5*inch))
    
    # Add sections
    sections_data = [
        ("【 COLLAPSE 】", "In the depths of dissolution, you faced the void:", collapse),
        ("【 COMPRESSION 】", "From the fragments, you forged something new:", build),
        ("【 CONVERGENCE 】", "Now, you stand transformed:", now)
    ]
    
    for title, intro, content in sections_data:
        elements.append(Paragraph(title, heading_style))
        elements.append(Paragraph(intro, body_style))
        # Quote the user content inside double quotes for emphasis
        elements.append(Paragraph(f'"{content}"', quote_style))
        elements.append(Spacer(1, 0.3*inch))
    
    # Archetype section
    elements.append(Paragraph("【 ARCHETYPE 】", heading_style))
    if archetype and archetype in ARCHETYPES:
        arch_data = ARCHETYPES[archetype]
        elements.append(Paragraph(
            f"You embody the {archetype.title()}: {arch_data['description']}",
            body_style
        ))
        # Quote the archetype's quote inside double quotes for clarity
        elements.append(Paragraph(
            f'"{arch_data["quote"]}"',
            quote_style
        ))
    else:
        elements.append(Paragraph("Your archetype is still crystallizing in the cosmic forge", body_style))
    
    elements.append(Spacer(1, 0.3*inch))
    
    # Synthesis
    elements.append(Paragraph("【 SYNTHESIS 】", heading_style))
    synthesis_text = """Your journey maps the eternal pattern:
    Dissolution → Crystallization → Emergence<br/><br/>
    What was broken has become the foundation.<br/>
    What was lost has become the compass.<br/>
    What remains is irreducibly you."""
    elements.append(Paragraph(synthesis_text, body_style))
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=f'reflexion_{datetime.now().strftime("%Y%m%d_%H%M%S")}.pdf',
        mimetype='application/pdf'
    )

@app.route('/api/archetypes')
def get_archetypes():
    """Return enhanced archetypes data"""
    return jsonify(ARCHETYPES)

@app.route('/api/guidance/<field>')
def get_field_guidance(field):
    """Get guidance for specific field"""
    return jsonify(FIELD_GUIDANCE.get(field, {}))

if __name__ == '__main__':
    app.run(debug=True, port=5000)