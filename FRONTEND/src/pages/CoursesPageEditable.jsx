import { useState, useEffect } from 'react';
import { BookOpen, GraduationCap, CheckCircle, Clock, AlertCircle, Loader, ChevronRight, Award, Edit2, Trash2, Plus, X, Save } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { academicApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import './CoursesPage.css';
import './CoursesPageEditable.css';

function CoursesPageEditable() {
  const { t } = useTranslation();
  const { isLoading: authLoading, accessToken } = useAuth();

  // State
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [degrees, setDegrees] = useState([]);
  const [selectedDegree, setSelectedDegree] = useState(null);
  const [curriculum, setCurriculum] = useState([]);
  const [subjects, setSubjects] = useState([]);
  const [schooling, setSchooling] = useState(null);
  const [plan, setPlan] = useState(null);
  const [activeTab, setActiveTab] = useState('progress');

  // Edit state
  const [editingSubject, setEditingSubject] = useState(null);
  const [showDegreeModal, setShowDegreeModal] = useState(false);
  const [showEnrollModal, setShowEnrollModal] = useState(false);
  const [selectedSubjectToEnroll, setSelectedSubjectToEnroll] = useState(null);

  // Form state
  const [gradeInput, setGradeInput] = useState('');
  const [semesterInput, setSemesterInput] = useState('');

  // Load data when authenticated
  useEffect(() => {
    if (!authLoading && accessToken) {
      loadDegrees();
    }
  }, [authLoading, accessToken]);

  // Load specific degree data when selected
  useEffect(() => {
    if (selectedDegree) {
      loadDegreeData(selectedDegree.degree_id);
    }
  }, [selectedDegree]);

  const loadDegrees = async () => {
    try {
      setLoading(true);
      setError(null);
      const degreesData = await academicApi.getDegrees();
      setDegrees(degreesData);

      // Auto-select first degree if available
      if (degreesData.length > 0) {
        setSelectedDegree(degreesData[0]);
      } else {
        setShowDegreeModal(true); // Show modal to enroll if no degrees
      }
    } catch (err) {
      console.error('Error loading degrees:', err);
      setError(t('courses.errorLoadingDegrees'));
    } finally {
      setLoading(false);
    }
  };

  const loadDegreeData = async (degreeId) => {
    try {
      setLoading(true);
      setError(null);

      const [curriculumData, subjectsData, schoolingData, planData] = await Promise.all([
        academicApi.getCurriculum(degreeId),
        academicApi.getDegreeSubjects(degreeId),
        academicApi.getMySchooling(degreeId).catch(() => null),
        academicApi.getMyPlan(degreeId).catch(() => null),
      ]);

      setCurriculum(curriculumData.curriculum || []);
      setSubjects(subjectsData);
      setSchooling(schoolingData);
      setPlan(planData);
    } catch (err) {
      console.error('Error loading degree data:', err);
      setError(t('courses.errorLoadingData'));
    } finally {
      setLoading(false);
    }
  };

  const handleEnrollInDegree = async (degreeId) => {
    try {
      await academicApi.enrollInDegree(degreeId);
      setShowDegreeModal(false);
      await loadDegrees();
    } catch (err) {
      console.error('Error enrolling in degree:', err);
      alert('Failed to enroll in degree');
    }
  };

  const handleUpdateGrade = async (subjectId) => {
    try {
      const grade = parseFloat(gradeInput);
      if (isNaN(grade) || grade < 0 || grade > 100) {
        alert(t('courses.invalidGrade'));
        return;
      }

      await academicApi.updateSubjectGrade(
        selectedDegree.degree_id,
        subjectId,
        grade,
        semesterInput
      );

      // Reload data
      await loadDegreeData(selectedDegree.degree_id);
      setEditingSubject(null);
      setGradeInput('');
      setSemesterInput('');
    } catch (err) {
      console.error('Error updating grade:', err);
      alert('Failed to update grade');
    }
  };

  const handleEnrollInSubject = async () => {
    try {
      if (!semesterInput) {
        alert(t('courses.semesterRequired'));
        return;
      }

      await academicApi.enrollInSubject(
        selectedDegree.degree_id,
        selectedSubjectToEnroll.subject_id,
        semesterInput
      );

      await loadDegreeData(selectedDegree.degree_id);
      setShowEnrollModal(false);
      setSelectedSubjectToEnroll(null);
      setSemesterInput('');
    } catch (err) {
      console.error('Error enrolling in subject:', err);
      alert('Failed to enroll in subject');
    }
  };

  const handleRemoveSubject = async (subjectId) => {
    if (!confirm(t('courses.confirmRemove'))) return;

    try {
      await academicApi.removeSubject(selectedDegree.degree_id, subjectId);
      await loadDegreeData(selectedDegree.degree_id);
    } catch (err) {
      console.error('Error removing subject:', err);
      alert('Failed to remove subject');
    }
  };

  // Helper functions
  const isSubjectCompleted = (subjectId) => {
    if (!schooling || !schooling.completed_subjects) return false;
    return schooling.completed_subjects.some(
      (s) => s.subject_id === subjectId && s.status === 'Passed'
    );
  };

  const isSubjectInProgress = (subjectId) => {
    if (!schooling || !schooling.in_progress_subjects) return false;
    return schooling.in_progress_subjects.some((s) => s.subject_id === subjectId);
  };

  const getSubjectGrade = (subjectId) => {
    if (!schooling || !schooling.completed_subjects) return null;
    const subject = schooling.completed_subjects.find((s) => s.subject_id === subjectId);
    return subject?.grade || null;
  };

  const arePrerequisitesMet = (prerequisites) => {
    if (!prerequisites || prerequisites.length === 0) return true;
    return prerequisites.every((prereq) => isSubjectCompleted(prereq));
  };

  // Render subject card with edit capabilities
  const renderSubjectCard = (subject, showPrerequisites = true) => {
    const completed = isSubjectCompleted(subject.subject_id);
    const inProgress = isSubjectInProgress(subject.subject_id);
    const grade = getSubjectGrade(subject.subject_id);
    const prereqsMet = arePrerequisitesMet(subject.prerequisites);

    let statusIcon, statusClass, statusText;

    if (completed) {
      statusIcon = <CheckCircle size={18} />;
      statusClass = 'status-completed';
      statusText = t('courses.completed');
    } else if (inProgress) {
      statusIcon = <Clock size={18} />;
      statusClass = 'status-inprogress';
      statusText = t('courses.inProgress');
    } else if (!prereqsMet) {
      statusIcon = <AlertCircle size={18} />;
      statusClass = 'status-locked';
      statusText = t('courses.locked');
    } else {
      statusClass = 'status-available';
      statusText = t('courses.available');
    }

    const isEditing = editingSubject === subject.subject_id;

    return (
      <div key={subject.subject_id} className={`subject-card ${statusClass}`}>
        <div className="subject-header">
          <div className="subject-code">{subject.subject_id}</div>
          <div className="subject-actions">
            {statusIcon && <div className="subject-status-icon">{statusIcon}</div>}
            {!completed && !inProgress && prereqsMet && (
              <button
                className="action-button enroll-button"
                onClick={() => {
                  setSelectedSubjectToEnroll(subject);
                  setShowEnrollModal(true);
                }}
                title={t('courses.enrollInSubject')}
              >
                <Plus size={16} />
              </button>
            )}
            {(completed || inProgress) && (
              <>
                <button
                  className="action-button edit-button"
                  onClick={() => {
                    setEditingSubject(subject.subject_id);
                    setGradeInput(grade || '');
                  }}
                  title={t('courses.editGrade')}
                >
                  <Edit2 size={16} />
                </button>
                <button
                  className="action-button delete-button"
                  onClick={() => handleRemoveSubject(subject.subject_id)}
                  title={t('courses.remove')}
                >
                  <Trash2 size={16} />
                </button>
              </>
            )}
          </div>
        </div>

        <div className="subject-name">{subject.name}</div>

        {isEditing ? (
          <div className="subject-edit-form">
            <input
              type="number"
              min="0"
              max="100"
              step="0.01"
              value={gradeInput}
              onChange={(e) => setGradeInput(e.target.value)}
              placeholder={t('courses.enterGrade')}
              className="grade-input"
            />
            <input
              type="text"
              value={semesterInput}
              onChange={(e) => setSemesterInput(e.target.value)}
              placeholder="2024-1"
              className="semester-input"
            />
            <div className="edit-actions">
              <button onClick={() => handleUpdateGrade(subject.subject_id)} className="save-button">
                <Save size={16} /> {t('courses.save')}
              </button>
              <button onClick={() => {
                setEditingSubject(null);
                setGradeInput('');
                setSemesterInput('');
              }} className="cancel-button">
                <X size={16} /> {t('courses.cancel')}
              </button>
            </div>
          </div>
        ) : (
          <>
            <div className="subject-info">
              <span className="subject-credits">
                {subject.credits} {t('courses.credits')}
              </span>
              {grade !== null && (
                <span className="subject-grade">
                  {t('courses.grade')}: {grade}
                </span>
              )}
            </div>
            {showPrerequisites && subject.prerequisites && subject.prerequisites.length > 0 && (
              <div className="subject-prerequisites">
                <small>
                  {t('courses.prerequisites')}: {subject.prerequisites.join(', ')}
                </small>
              </div>
            )}
            <div className={`subject-status-label ${statusClass}`}>{statusText}</div>
          </>
        )}
      </div>
    );
  };

  // Render Progress Tab
  const renderProgressTab = () => {
    if (!schooling) {
      return (
        <div className="empty-state">
          <BookOpen size={48} className="empty-icon" />
          <p>{t('courses.noProgressData')}</p>
        </div>
      );
    }

    const completedSubjects = schooling.completed_subjects || [];
    const inProgressSubjects = schooling.in_progress_subjects || [];

    return (
      <div className="progress-container">
        <div className="stats-grid">
          <div className="stat-card">
            <div className="stat-icon completed">
              <CheckCircle size={24} />
            </div>
            <div className="stat-content">
              <div className="stat-value">{completedSubjects.length}</div>
              <div className="stat-label">{t('courses.completedSubjects')}</div>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon inprogress">
              <Clock size={24} />
            </div>
            <div className="stat-content">
              <div className="stat-value">{inProgressSubjects.length}</div>
              <div className="stat-label">{t('courses.currentSubjects')}</div>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon credits">
              <Award size={24} />
            </div>
            <div className="stat-content">
              <div className="stat-value">{schooling.total_credits_earned}</div>
              <div className="stat-label">{t('courses.creditsEarned')}</div>
            </div>
          </div>

          <div className="stat-card">
            <div className="stat-icon gpa">
              <GraduationCap size={24} />
            </div>
            <div className="stat-content">
              <div className="stat-value">{schooling.gpa.toFixed(2)}</div>
              <div className="stat-label">{t('courses.gpa')}</div>
            </div>
          </div>
        </div>

        {inProgressSubjects.length > 0 && (
          <div className="subjects-section">
            <h3>
              <Clock size={20} />
              {t('courses.currentSubjects')}
            </h3>
            <div className="subjects-grid">
              {inProgressSubjects.map((subject) => {
                const fullSubject = subjects.find((s) => s.subject_id === subject.subject_id);
                return fullSubject ? renderSubjectCard(fullSubject, false) : null;
              })}
            </div>
          </div>
        )}

        {completedSubjects.length > 0 && (
          <div className="subjects-section">
            <h3>
              <CheckCircle size={20} />
              {t('courses.completedSubjects')}
            </h3>
            <div className="subjects-grid">
              {completedSubjects.map((subject) => {
                const fullSubject = subjects.find((s) => s.subject_id === subject.subject_id);
                return fullSubject ? renderSubjectCard(fullSubject, false) : null;
              })}
            </div>
          </div>
        )}
      </div>
    );
  };

  // Render Curriculum Tab
  const renderCurriculumTab = () => {
    if (curriculum.length === 0) {
      return (
        <div className="empty-state">
          <BookOpen size={48} className="empty-icon" />
          <p>{t('courses.noCurriculumData')}</p>
        </div>
      );
    }

    return (
      <div className="curriculum-container">
        {curriculum.map((semester) => (
          <div key={semester.semester} className="semester-section">
            <h3 className="semester-title">
              {t('courses.semester')} {semester.semester}
            </h3>
            <div className="subjects-grid">
              {semester.subjects.map((subject) => {
                const fullSubject = subjects.find((s) => s.subject_id === subject.subject_id);
                return fullSubject ? renderSubjectCard(fullSubject) : null;
              })}
            </div>
          </div>
        ))}
      </div>
    );
  };

  // Render Plan Tab
  const renderPlanTab = () => {
    if (!plan || !plan.semester_plans || plan.semester_plans.length === 0) {
      return (
        <div className="empty-state">
          <BookOpen size={48} className="empty-icon" />
          <p>{t('courses.noPlanData')}</p>
          <p className="empty-hint">{t('courses.createPlanHint')}</p>
        </div>
      );
    }

    return (
      <div className="plan-container">
        {plan.semester_plans.map((semesterPlan) => (
          <div key={semesterPlan.semester} className="semester-section">
            <h3 className="semester-title">
              {semesterPlan.semester}
              <span className="semester-credits">
                ({semesterPlan.total_credits} {t('courses.credits')})
              </span>
            </h3>
            {semesterPlan.notes && <p className="semester-notes">{semesterPlan.notes}</p>}
            <div className="subjects-grid">
              {semesterPlan.planned_subjects.map((plannedSubject) => {
                const fullSubject = subjects.find((s) => s.subject_id === plannedSubject.subject_id);
                return fullSubject ? renderSubjectCard(fullSubject) : null;
              })}
            </div>
          </div>
        ))}
      </div>
    );
  };

  if (loading && degrees.length === 0) {
    return (
      <div className="courses-page">
        <div className="loading-container">
          <Loader className="spinner" size={48} />
          <p>{t('courses.loading')}</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="courses-page">
        <div className="error-container">
          <AlertCircle size={48} className="error-icon" />
          <p>{error}</p>
        </div>
      </div>
    );
  }

  if (degrees.length === 0) {
    return (
      <div className="courses-page">
        <div className="empty-state">
          <GraduationCap size={64} className="empty-icon" />
          <h2>{t('courses.noDegrees')}</h2>
          <p>{t('courses.noDegreesHint')}</p>
          <button className="primary-button" onClick={() => setShowDegreeModal(true)}>
            {t('courses.enrollInDegree')}
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="courses-page">
      {/* Header */}
      <div className="courses-header">
        <div className="header-content">
          <div className="header-icon">
            <GraduationCap size={32} />
          </div>
          <div>
            <h1>{t('courses.title')}</h1>
            {selectedDegree && (
              <p className="degree-info">
                {selectedDegree.degree_name} - {selectedDegree.total_credits} {t('courses.totalCredits')}
              </p>
            )}
          </div>
        </div>
      </div>

      {/* Tabs */}
      <div className="tabs-container">
        <button
          className={`tab ${activeTab === 'progress' ? 'active' : ''}`}
          onClick={() => setActiveTab('progress')}
        >
          <CheckCircle size={18} />
          {t('courses.myProgress')}
        </button>
        <button
          className={`tab ${activeTab === 'curriculum' ? 'active' : ''}`}
          onClick={() => setActiveTab('curriculum')}
        >
          <BookOpen size={18} />
          {t('courses.curriculum')}
        </button>
        <button
          className={`tab ${activeTab === 'plan' ? 'active' : ''}`}
          onClick={() => setActiveTab('plan')}
        >
          <Clock size={18} />
          {t('courses.studyPlan')}
        </button>
      </div>

      {/* Content */}
      <div className="tab-content">
        {loading ? (
          <div className="loading-container">
            <Loader className="spinner" size={32} />
          </div>
        ) : (
          <>
            {activeTab === 'progress' && renderProgressTab()}
            {activeTab === 'curriculum' && renderCurriculumTab()}
            {activeTab === 'plan' && renderPlanTab()}
          </>
        )}
      </div>

      {/* Degree Selection Modal */}
      {showDegreeModal && (
        <div className="modal-overlay" onClick={() => setShowDegreeModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>{t('courses.selectDegree')}</h2>
            <div className="degree-list">
              {degrees.map((degree) => (
                <div key={degree.degree_id} className="degree-item">
                  <div>
                    <h3>{degree.degree_name}</h3>
                    <p>{degree.description}</p>
                    <small>{degree.total_credits} {t('courses.credits')} - {degree.duration_semesters} {t('courses.semesters')}</small>
                  </div>
                  <button
                    onClick={() => handleEnrollInDegree(degree.degree_id)}
                    className="primary-button"
                  >
                    {t('courses.enroll')}
                  </button>
                </div>
              ))}
            </div>
            <button onClick={() => setShowDegreeModal(false)} className="secondary-button">
              {t('courses.cancel')}
            </button>
          </div>
        </div>
      )}

      {/* Subject Enrollment Modal */}
      {showEnrollModal && selectedSubjectToEnroll && (
        <div className="modal-overlay" onClick={() => setShowEnrollModal(false)}>
          <div className="modal-content" onClick={(e) => e.stopPropagation()}>
            <h2>{t('courses.enrollInSubject')}</h2>
            <p><strong>{selectedSubjectToEnroll.name}</strong></p>
            <p>{selectedSubjectToEnroll.subject_id} - {selectedSubjectToEnroll.credits} {t('courses.credits')}</p>
            <input
              type="text"
              value={semesterInput}
              onChange={(e) => setSemesterInput(e.target.value)}
              placeholder="2024-2"
              className="semester-input"
            />
            <div className="modal-actions">
              <button onClick={handleEnrollInSubject} className="primary-button">
                {t('courses.enroll')}
              </button>
              <button onClick={() => setShowEnrollModal(false)} className="secondary-button">
                {t('courses.cancel')}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default CoursesPageEditable;
