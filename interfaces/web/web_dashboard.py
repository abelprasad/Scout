from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from shared.database.database import get_db_session, InternshipListing, AgentJob, mark_as_applied
from sqlalchemy import func, or_
import json
from datetime import datetime
from typing import Optional

app = FastAPI(title="Internship Database Dashboard")

@app.get("/", response_class=HTMLResponse)
def dashboard():
    """Main dashboard with CRUD interface"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Internship Database</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body { 
                font-family: 'SF Pro Text', -apple-system, BlinkMacSystemFont, 'Inter', system-ui, sans-serif; 
                background: #0a0a0a; 
                color: #e4e4e7; 
                line-height: 1.6;
            }

            .container { max-width: 1200px; margin: 0 auto; padding: 40px 20px; }

            .header { 
                margin-bottom: 48px; 
                border-bottom: 1px solid #27272a; 
                padding-bottom: 24px; 
            }
            .header h1 { 
                font-size: 24px; 
                font-weight: 600; 
                color: #fafafa; 
                margin-bottom: 8px; 
            }
            .header p { 
                color: #a1a1aa; 
                font-size: 14px; 
            }

            .stats { 
                display: grid; 
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); 
                gap: 16px; 
                margin-bottom: 48px; 
            }
            .stat-card { 
                background: #18181b; 
                border: 1px solid #27272a; 
                padding: 24px; 
                border-radius: 8px; 
            }
            .stat-card h3 { 
                font-size: 12px; 
                font-weight: 500; 
                color: #71717a; 
                text-transform: uppercase; 
                letter-spacing: 0.05em; 
                margin-bottom: 8px; 
            }
            .stat-card .number { 
                font-size: 32px; 
                font-weight: 700; 
                color: #fafafa; 
            }

            .controls { 
                background: #18181b; 
                border: 1px solid #27272a; 
                padding: 24px; 
                border-radius: 8px; 
                margin-bottom: 24px; 
            }
            .controls h3 { 
                font-size: 14px; 
                font-weight: 600; 
                color: #fafafa; 
                margin-bottom: 16px; 
            }

            .filter-row { 
                display: flex; 
                gap: 16px; 
                align-items: end; 
                flex-wrap: wrap; 
            }
            .form-group { 
                flex: 1; 
                min-width: 180px; 
            }
            .form-group label { 
                display: block; 
                font-size: 12px; 
                font-weight: 500; 
                color: #a1a1aa; 
                margin-bottom: 6px; 
                text-transform: uppercase; 
                letter-spacing: 0.05em; 
            }
            .form-group input, .form-group select { 
                width: 100%; 
                padding: 12px; 
                background: #0a0a0a; 
                border: 1px solid #27272a; 
                border-radius: 6px; 
                color: #fafafa; 
                font-size: 14px; 
            }
            .form-group input:focus, .form-group select:focus { 
                outline: none; 
                border-color: #3f3f46; 
            }

            .btn { 
                padding: 12px 16px; 
                background: #fafafa; 
                color: #0a0a0a; 
                border: none; 
                border-radius: 6px; 
                cursor: pointer; 
                font-weight: 500; 
                font-size: 14px; 
                transition: all 0.2s; 
            }
            .btn:hover { 
                background: #e4e4e7; 
            }
            .btn-secondary { 
                background: #27272a; 
                color: #fafafa; 
            }
            .btn-secondary:hover { 
                background: #3f3f46; 
            }
            .btn-danger { 
                background: #dc2626; 
                color: #fafafa; 
            }
            .btn-danger:hover { 
                background: #b91c1c; 
            }
            .btn-success { 
                background: #16a34a; 
                color: #fafafa; 
            }
            .btn-success:hover { 
                background: #15803d; 
            }

            .internships { 
                background: #18181b; 
                border: 1px solid #27272a; 
                border-radius: 8px; 
            }

            .internships-header { 
                padding: 24px; 
                border-bottom: 1px solid #27272a; 
            }
            .internships-header h2 { 
                font-size: 16px; 
                font-weight: 600; 
                color: #fafafa; 
            }

            .internship { 
                padding: 24px; 
                border-bottom: 1px solid #27272a; 
                display: flex; 
                justify-content: space-between; 
                align-items: start; 
                transition: background 0.2s; 
            }
            .internship:last-child { 
                border-bottom: none; 
            }
            .internship:hover { 
                background: #0f0f10; 
            }

            .internship-info { 
                flex: 1; 
            }
            .title { 
                font-weight: 600; 
                color: #fafafa; 
                margin-bottom: 6px; 
                font-size: 15px; 
            }
            .company { 
                color: #a1a1aa; 
                margin-bottom: 4px; 
                font-size: 14px; 
            }
            .meta { 
                color: #71717a; 
                font-size: 13px; 
                margin-bottom: 8px; 
            }
            .url { 
                color: #a1a1aa; 
                text-decoration: none; 
                font-size: 13px; 
                opacity: 0.8; 
            }
            .url:hover { 
                opacity: 1; 
                text-decoration: underline; 
            }

            .internship-actions { 
                display: flex; 
                gap: 12px; 
                flex-direction: column; 
                align-items: end; 
            }

            .status { 
                padding: 4px 8px; 
                border-radius: 4px; 
                font-size: 11px; 
                font-weight: 500; 
                text-transform: uppercase; 
                letter-spacing: 0.05em; 
            }
            .status.applied { 
                background: #166534; 
                color: #bbf7d0; 
            }
            .status.not-applied { 
                background: #27272a; 
                color: #a1a1aa; 
            }
            .status.interviewing {
                background: #ca8a04;
                color: #fef3c7;
            }

            .score-badge {
                padding: 4px 10px;
                border-radius: 4px;
                font-size: 12px;
                font-weight: 600;
                margin-bottom: 8px;
            }
            .score-high {
                background: #166534;
                color: #bbf7d0;
            }
            .score-medium {
                background: #854d0e;
                color: #fef3c7;
            }
            .score-low {
                background: #27272a;
                color: #a1a1aa;
            }

            .action-btns { 
                display: flex; 
                gap: 8px; 
                margin-top: 12px; 
            }
            .btn-sm { 
                padding: 6px 10px; 
                font-size: 12px; 
                font-weight: 500; 
            }

            .modal { 
                display: none; 
                position: fixed; 
                top: 0; 
                left: 0; 
                width: 100%; 
                height: 100%; 
                background: rgba(0,0,0,0.8); 
                z-index: 1000; 
                backdrop-filter: blur(4px); 
            }
            .modal-content { 
                background: #18181b; 
                border: 1px solid #27272a; 
                margin: 60px auto; 
                padding: 32px; 
                border-radius: 8px; 
                max-width: 480px; 
            }
            .modal h3 { 
                font-size: 18px; 
                font-weight: 600; 
                color: #fafafa; 
                margin-bottom: 24px; 
            }
            .form-row { 
                margin-bottom: 16px; 
            }
            .form-row label { 
                display: block; 
                font-size: 12px; 
                font-weight: 500; 
                color: #a1a1aa; 
                margin-bottom: 6px; 
                text-transform: uppercase; 
                letter-spacing: 0.05em; 
            }
            .form-row input, .form-row textarea, .form-row select { 
                width: 100%; 
                padding: 12px; 
                background: #0a0a0a; 
                border: 1px solid #27272a; 
                border-radius: 6px; 
                color: #fafafa; 
                font-size: 14px; 
            }
            .form-row textarea { 
                height: 80px; 
                resize: vertical; 
                font-family: inherit; 
            }
            .form-row input:focus, .form-row textarea:focus, .form-row select:focus { 
                outline: none; 
                border-color: #3f3f46; 
            }

            @media (max-width: 768px) {
                .container { padding: 24px 16px; }
                .internship { flex-direction: column; gap: 16px; }
                .internship-actions { flex-direction: row; align-items: center; }
                .filter-row { flex-direction: column; align-items: stretch; }
                .form-group { min-width: unset; }
            }
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>Internship Database</h1>
                <p>Self-hosted autonomous internship discovery and management system</p>
            </div>
            
            <div class="stats" id="stats">
                <div class="stat-card">
                    <h3>Total Internships</h3>
                    <div class="number" id="total-count">-</div>
                </div>
                <div class="stat-card">
                    <h3>Applied</h3>
                    <div class="number" id="applied-count">-</div>
                </div>
                <div class="stat-card">
                    <h3>Interviewing</h3>
                    <div class="number" id="interviewing-count">-</div>
                </div>
                <div class="stat-card">
                    <h3>This Week</h3>
                    <div class="number" id="week-count">-</div>
                </div>
            </div>
            
            <div class="controls">
                <h3>Search & Filter</h3>
                <div class="filter-row">
                    <div class="form-group">
                        <label>Search</label>
                        <input type="text" id="search-input" placeholder="Search title, company, or description...">
                    </div>
                    <div class="form-group">
                        <label>Status</label>
                        <select id="status-filter">
                            <option value="">All Statuses</option>
                            <option value="not_applied">Not Applied</option>
                            <option value="applied">Applied</option>
                            <option value="interviewing">Interviewing</option>
                            <option value="rejected">Rejected</option>
                            <option value="offer">Offer</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Sort By</label>
                        <select id="sort-filter" onchange="loadData()">
                            <option value="relevance">Best Match</option>
                            <option value="posted">Recently Posted</option>
                            <option value="date">Recently Found</option>
                            <option value="company">Company A-Z</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <button class="btn" onclick="searchInternships()">Search</button>
                    </div>
                    <div class="form-group">
                        <button class="btn btn-secondary" onclick="showAddModal()">Add Internship</button>
                    </div>
                </div>
            </div>
            
            <div class="internships">
                <div class="internships-header">
                    <h2>Internship Opportunities</h2>
                </div>
                <div id="internship-list">Loading...</div>
            </div>
        </div>
        
        <!-- Edit Modal -->
        <div id="edit-modal" class="modal">
            <div class="modal-content">
                <h3>Edit Internship</h3>
                <form id="edit-form">
                    <input type="hidden" id="edit-id">
                    <div class="form-row">
                        <label>Title</label>
                        <input type="text" id="edit-title" required>
                    </div>
                    <div class="form-row">
                        <label>Company</label>
                        <input type="text" id="edit-company" required>
                    </div>
                    <div class="form-row">
                        <label>Location</label>
                        <input type="text" id="edit-location">
                    </div>
                    <div class="form-row">
                        <label>URL</label>
                        <input type="url" id="edit-url">
                    </div>
                    <div class="form-row">
                        <label>Status</label>
                        <select id="edit-status">
                            <option value="not_applied">Not Applied</option>
                            <option value="applied">Applied</option>
                            <option value="interviewing">Interviewing</option>
                            <option value="rejected">Rejected</option>
                            <option value="offer">Offer</option>
                        </select>
                    </div>
                    <div class="form-row">
                        <label>Notes</label>
                        <textarea id="edit-notes" placeholder="Application notes, interview feedback, etc."></textarea>
                    </div>
                    <div style="display: flex; gap: 10px; justify-content: end;">
                        <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                        <button type="submit" class="btn">Save Changes</button>
                    </div>
                </form>
            </div>
        </div>
        
        <!-- Add Modal -->
        <div id="add-modal" class="modal">
            <div class="modal-content">
                <h3>Add New Internship</h3>
                <form id="add-form">
                    <div class="form-row">
                        <label>Title</label>
                        <input type="text" id="add-title" required>
                    </div>
                    <div class="form-row">
                        <label>Company</label>
                        <input type="text" id="add-company" required>
                    </div>
                    <div class="form-row">
                        <label>Location</label>
                        <input type="text" id="add-location">
                    </div>
                    <div class="form-row">
                        <label>URL</label>
                        <input type="url" id="add-url">
                    </div>
                    <div class="form-row">
                        <label>Notes</label>
                        <textarea id="add-notes" placeholder="Application notes, requirements, etc."></textarea>
                    </div>
                    <div style="display: flex; gap: 10px; justify-content: end;">
                        <button type="button" class="btn btn-secondary" onclick="closeModal()">Cancel</button>
                        <button type="submit" class="btn">Add Internship</button>
                    </div>
                </form>
            </div>
        </div>
        
        <script>
            let currentInternships = [];
            
            async function loadData() {
                try {
                    const sortBy = document.getElementById('sort-filter')?.value || 'relevance';
                    const [statsResponse, internshipsResponse] = await Promise.all([
                        fetch('/api/stats'),
                        fetch(`/api/internships?limit=100&sort=${sortBy}`)
                    ]);
                    
                    const stats = await statsResponse.json();
                    const internships = await internshipsResponse.json();
                    
                    currentInternships = internships;
                    
                    // Update stats
                    document.getElementById('total-count').textContent = stats.total;
                    document.getElementById('applied-count').textContent = stats.applied;
                    document.getElementById('interviewing-count').textContent = stats.interviewing;
                    document.getElementById('week-count').textContent = stats.this_week;
                    
                    displayInternships(internships);
                } catch (error) {
                    document.getElementById('internship-list').innerHTML = '<div style="padding: 20px; text-align: center; color: #e53e3e;">Error loading data</div>';
                }
            }
            
            function displayInternships(internships) {
                const listEl = document.getElementById('internship-list');
                if (internships.length === 0) {
                    listEl.innerHTML = '<div style="padding: 20px; text-align: center; color: #71717a;">No internships found</div>';
                    return;
                }
                
                listEl.innerHTML = internships.map(internship => `
                    <div class="internship">
                        <div class="internship-info">
                            <div class="title">${internship.title}</div>
                            <div class="company">${internship.company}</div>
                            <div class="meta">${internship.location || 'Location not specified'} ${internship.age_days ? `• Posted ${internship.age_days}d ago` : ''} • Found: ${new Date(internship.discovered_at).toLocaleDateString()}</div>
                            ${internship.url ? `<a href="${internship.url}" target="_blank" class="url">View Posting</a>` : ''}
                        </div>
                        <div class="internship-actions">
                            ${internship.relevance_score > 0 ? `<span class="score-badge ${getScoreClass(internship.relevance_score)}">${internship.relevance_score}% Match</span>` : ''}
                            <span class="status ${internship.application_status || 'not-applied'}">${formatStatus(internship.application_status || 'not_applied')}</span>
                            <div class="action-btns">
                                <button class="btn btn-sm" onclick="editInternship(${internship.id})">Edit</button>
                                ${internship.application_status === 'not_applied' || !internship.application_status ?
                                    `<button class="btn btn-sm btn-success" onclick="markAsApplied(${internship.id})">Applied</button>` :
                                    ''}
                                <button class="btn btn-sm btn-danger" onclick="deleteInternship(${internship.id})">Delete</button>
                            </div>
                        </div>
                    </div>
                `).join('');
            }
            
            function formatStatus(status) {
                const statusMap = {
                    'not_applied': 'Not Applied',
                    'applied': 'Applied',
                    'interviewing': 'Interviewing',
                    'rejected': 'Rejected',
                    'offer': 'Offer'
                };
                return statusMap[status] || status;
            }

            function getScoreClass(score) {
                if (score >= 60) return 'score-high';
                if (score >= 30) return 'score-medium';
                return 'score-low';
            }
            
            function searchInternships() {
                const searchTerm = document.getElementById('search-input').value.toLowerCase();
                const statusFilter = document.getElementById('status-filter').value;
                
                let filtered = currentInternships;
                
                if (searchTerm) {
                    filtered = filtered.filter(internship => 
                        internship.title.toLowerCase().includes(searchTerm) ||
                        internship.company.toLowerCase().includes(searchTerm) ||
                        (internship.description && internship.description.toLowerCase().includes(searchTerm))
                    );
                }
                
                if (statusFilter) {
                    filtered = filtered.filter(internship => 
                        (internship.application_status || 'not_applied') === statusFilter
                    );
                }
                
                displayInternships(filtered);
            }
            
            async function markAsApplied(id) {
                try {
                    const response = await fetch(`/api/internships/${id}/apply`, {
                        method: 'POST'
                    });
                    if (response.ok) {
                        loadData(); // Refresh
                    }
                } catch (error) {
                    alert('Error updating status');
                }
            }
            
            async function deleteInternship(id) {
                if (confirm('Are you sure you want to delete this internship?')) {
                    try {
                        const response = await fetch(`/api/internships/${id}`, {
                            method: 'DELETE'
                        });
                        if (response.ok) {
                            loadData(); // Refresh
                        }
                    } catch (error) {
                        alert('Error deleting internship');
                    }
                }
            }
            
            function editInternship(id) {
                const internship = currentInternships.find(i => i.id === id);
                if (!internship) return;
                
                document.getElementById('edit-id').value = internship.id;
                document.getElementById('edit-title').value = internship.title;
                document.getElementById('edit-company').value = internship.company;
                document.getElementById('edit-location').value = internship.location || '';
                document.getElementById('edit-url').value = internship.url || '';
                document.getElementById('edit-status').value = internship.application_status || 'not_applied';
                document.getElementById('edit-notes').value = internship.notes || '';
                
                document.getElementById('edit-modal').style.display = 'block';
            }
            
            function showAddModal() {
                document.getElementById('add-form').reset();
                document.getElementById('add-modal').style.display = 'block';
            }
            
            function closeModal() {
                document.getElementById('edit-modal').style.display = 'none';
                document.getElementById('add-modal').style.display = 'none';
            }
            
            // Form submissions
            document.getElementById('edit-form').addEventListener('submit', async (e) => {
                e.preventDefault();
                const id = document.getElementById('edit-id').value;
                const data = {
                    title: document.getElementById('edit-title').value,
                    company: document.getElementById('edit-company').value,
                    location: document.getElementById('edit-location').value,
                    url: document.getElementById('edit-url').value,
                    application_status: document.getElementById('edit-status').value,
                    notes: document.getElementById('edit-notes').value
                };
                
                try {
                    const response = await fetch(`/api/internships/${id}`, {
                        method: 'PUT',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(data)
                    });
                    if (response.ok) {
                        closeModal();
                        loadData();
                    }
                } catch (error) {
                    alert('Error updating internship');
                }
            });
            
            document.getElementById('add-form').addEventListener('submit', async (e) => {
                e.preventDefault();
                const data = {
                    title: document.getElementById('add-title').value,
                    company: document.getElementById('add-company').value,
                    location: document.getElementById('add-location').value,
                    url: document.getElementById('add-url').value,
                    notes: document.getElementById('add-notes').value
                };
                
                try {
                    const response = await fetch('/api/internships', {
                        method: 'POST',
                        headers: {'Content-Type': 'application/json'},
                        body: JSON.stringify(data)
                    });
                    if (response.ok) {
                        closeModal();
                        loadData();
                    }
                } catch (error) {
                    alert('Error adding internship');
                }
            });
            
            // Close modal when clicking outside
            window.addEventListener('click', (e) => {
                if (e.target.classList.contains('modal')) {
                    closeModal();
                }
            });
            
            // Load data on page load and set up refresh
            loadData();
            setInterval(loadData, 60000); // Refresh every minute
        </script>
    </body>
    </html>
    """

@app.get("/api/stats")
def get_stats():
    """Get database statistics"""
    session = get_db_session()
    
    total = session.query(InternshipListing).count()
    applied = session.query(InternshipListing).filter_by(application_status="applied").count()
    interviewing = session.query(InternshipListing).filter_by(application_status="interviewing").count()
    
    # This week count
    from datetime import datetime, timedelta
    week_ago = datetime.now() - timedelta(days=7)
    this_week = session.query(InternshipListing).filter(InternshipListing.discovered_at >= week_ago).count()
    
    session.close()
    
    return {
        "total": total,
        "applied": applied,
        "interviewing": interviewing,
        "this_week": this_week
    }

@app.get("/api/internships")
def get_internships(search: Optional[str] = None, status: Optional[str] = None, sort: Optional[str] = "relevance", limit: int = 50):
    """Get internships with optional filtering"""
    session = get_db_session()

    query = session.query(InternshipListing)

    if search:
        query = query.filter(
            or_(
                InternshipListing.title.contains(search),
                InternshipListing.company.contains(search),
                InternshipListing.description.contains(search)
            )
        )

    if status:
        query = query.filter(InternshipListing.application_status == status)

    # Sort options
    if sort == "relevance":
        internships = query.order_by(InternshipListing.relevance_score.desc()).limit(limit).all()
    elif sort == "posted":
        # Sort by age_days ascending (newest posts = lowest age_days)
        internships = query.order_by(InternshipListing.age_days.asc().nullslast()).limit(limit).all()
    elif sort == "date":
        internships = query.order_by(InternshipListing.discovered_at.desc()).limit(limit).all()
    elif sort == "company":
        internships = query.order_by(InternshipListing.company.asc()).limit(limit).all()
    else:
        internships = query.order_by(InternshipListing.relevance_score.desc()).limit(limit).all()

    result = []
    for internship in internships:
        result.append({
            "id": internship.id,
            "title": internship.title,
            "company": internship.company,
            "url": internship.url,
            "location": internship.location,
            "description": internship.description,
            "discovered_at": internship.discovered_at.isoformat(),
            "application_status": internship.application_status,
            "applied": internship.applied,
            "notes": internship.notes,
            "relevance_score": internship.relevance_score or 0,
            "age_days": internship.age_days
        })

    session.close()
    return result

@app.post("/api/internships")
def create_internship(data: dict):
    """Create new internship"""
    session = get_db_session()
    
    internship = InternshipListing(
        agent_job_id="manual",
        title=data.get("title", ""),
        company=data.get("company", ""),
        location=data.get("location", ""),
        url=data.get("url", ""),
        notes=data.get("notes", "")
    )
    
    session.add(internship)
    session.commit()
    session.close()
    
    return {"success": True}

@app.put("/api/internships/{internship_id}")
def update_internship(internship_id: int, data: dict):
    """Update internship"""
    session = get_db_session()
    
    internship = session.query(InternshipListing).get(internship_id)
    if not internship:
        session.close()
        raise HTTPException(status_code=404, detail="Internship not found")
    
    # Update fields
    for key, value in data.items():
        if hasattr(internship, key):
            setattr(internship, key, value)
    
    # Set application date if marking as applied
    if data.get('application_status') == 'applied' and not internship.applied:
        internship.applied = True
        internship.application_date = datetime.utcnow()
    
    session.commit()
    session.close()
    
    return {"success": True}

@app.post("/api/internships/{internship_id}/apply")
def mark_internship_applied(internship_id: int):
    """Mark internship as applied"""
    session = get_db_session()
    
    internship = session.query(InternshipListing).get(internship_id)
    if not internship:
        session.close()
        raise HTTPException(status_code=404, detail="Internship not found")
    
    internship.applied = True
    internship.application_status = "applied"
    internship.application_date = datetime.utcnow()
    
    session.commit()
    session.close()
    
    return {"success": True}

@app.delete("/api/internships/{internship_id}")
def delete_internship(internship_id: int):
    """Delete internship"""
    session = get_db_session()
    
    internship = session.query(InternshipListing).get(internship_id)
    if not internship:
        session.close()
        raise HTTPException(status_code=404, detail="Internship not found")
    
    session.delete(internship)
    session.commit()
    session.close()
    
    return {"success": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
