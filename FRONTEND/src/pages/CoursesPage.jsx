import { useState, useEffect } from 'react';
import { BookOpen, GraduationCap, CheckCircle, Clock, AlertCircle, Loader, ChevronRight, Award } from 'lucide-react';
import { useTranslation } from 'react-i18next';
import { academicApi } from '../services/api';
import { useAuth } from '../context/AuthContext';
import './CoursesPage.css';

function CoursesPage() {
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
  const [activeTab, setActiveTab] = useState('progress'); // 'progress', 'curriculum', 'plan'

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

      // Load curriculum, subjects, schooling, and plan in parallel
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

  // Helper to check if a subject is completed
  const isSubjectCompleted = (subjectId) => {
    if (!schooling || !schooling.completed_subjects) return false;
    return schooling.completed_subjects.some(
      (s) => s.subject_id === subjectId && s.status === 'Passed'
    );
  };

  // Helper to check if a subject is in progress
  const isSubjectInProgress = (subjectId) => {
    if (!schooling || !schooling.in_progress_subjects) return false;
    return schooling.in_progress_subjects.some((s) => s.subject_id === subjectId);
  };

  // Helper to get subject grade
  const getSubjectGrade = (subjectId) => {
    if (!schooling || !schooling.completed_subjects) return null;
    const subject = schooling.completed_subjects.find((s) => s.subject_id === subjectId);
    return subject?.grade || null;
  };

  // Helper to check if prerequisites are met
  const arePrerequisitesMet = (prerequisites) => {
    if (!prerequisites || prerequisites.length === 0) return true;
    return prerequisites.every((prereq) => isSubjectCompleted(prereq));
  };

  // Render subject card
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

    return (
      <div key={subject.subject_id} className={`subject-card ${statusClass}`}>
        <div className="subject-header">
          <div className="subject-code">{subject.subject_id}</div>
          {statusIcon && <div className="subject-status-icon">{statusIcon}</div>}
        </div>
        <div className="subject-name">{subject.name}</div>
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
        {/* Stats Card */}
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

        {/* Current Subjects */}
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

        {/* Completed Subjects */}
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
    </div>
  );
}

export default CoursesPage;
