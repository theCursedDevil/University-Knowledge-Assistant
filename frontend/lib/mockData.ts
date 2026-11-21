export type Role = "student" | "faculty" | "admin";

export interface UserProfile {
  id: string;
  name: string;
  email: string;
  role: Role;
  enrollmentNo?: string;
  department?: string;
  avatarUrl?: string;
  createdAt: string;
  status: "active" | "disabled";
}

export interface SuggestedQuestionCategory {
  id: string;
  name: string;
  iconName: string;
  questions: string[];
}

export interface CitationItem {
  id: string;
  document: string;
  page: number;
  section?: string;
  snippet: string;
  relevanceScore: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  createdAt: string;
  citations?: CitationItem[];
}

export interface ConversationThread {
  id: string;
  title: string;
  userId: string;
  createdAt: string;
  updatedAt: string;
  messageCount: number;
}

export interface DocumentItem {
  id: string;
  title: string;
  filename: string;
  category: "Academic" | "Examinations" | "Hostel" | "Placements" | "Admissions" | "General";
  pageCount: number;
  chunkCount: number;
  fileSize: string;
  status: "ready" | "processing" | "failed";
  uploadedBy: string;
  createdAt: string;
  updatedAt: string;
  version: number;
  description: string;
}

export interface AnalyticsMetric {
  title: string;
  value: string;
  change: string;
  trend: "up" | "down" | "neutral";
  description: string;
}

// ---------------------------------------------------------------------------
// 1. Initial Mock Users
// ---------------------------------------------------------------------------

export const MOCK_USERS: UserProfile[] = [
  {
    id: "usr-001",
    name: "Aashu Kumar",
    email: "student@university.edu",
    role: "student",
    enrollmentNo: "BT23GCS449",
    department: "Computer Science & Engineering (AI/ML)",
    createdAt: "2026-08-01T10:00:00Z",
    status: "active",
  },
  {
    id: "usr-002",
    name: "Dr. Ramesh Sharma",
    email: "faculty@university.edu",
    role: "faculty",
    enrollmentNo: "FAC-CS-104",
    department: "School of Computing & Data Science",
    createdAt: "2024-03-15T09:30:00Z",
    status: "active",
  },
  {
    id: "usr-003",
    name: "University Administrator",
    email: "admin@university.edu",
    role: "admin",
    enrollmentNo: "ADM-HQ-01",
    department: "Office of Academic Registrar",
    createdAt: "2023-01-10T08:00:00Z",
    status: "active",
  },
  {
    id: "usr-004",
    name: "Priya Nair",
    email: "priya.nair@university.edu",
    role: "student",
    enrollmentNo: "BT23GCS112",
    department: "Electronics & Communication Engineering",
    createdAt: "2026-08-02T11:15:00Z",
    status: "active",
  },
  {
    id: "usr-005",
    name: "Prof. Ananya Sen",
    email: "ananya.sen@university.edu",
    role: "faculty",
    enrollmentNo: "FAC-MATH-202",
    department: "Department of Mathematics",
    createdAt: "2022-07-20T14:00:00Z",
    status: "active",
  },
  {
    id: "usr-006",
    name: "Vikram Malhotra",
    email: "vikram.m@university.edu",
    role: "student",
    enrollmentNo: "BT22ME045",
    department: "Mechanical Engineering",
    createdAt: "2025-08-01T12:00:00Z",
    status: "disabled",
  },
];

// ---------------------------------------------------------------------------
// 2. Suggested Questions (W-16)
// ---------------------------------------------------------------------------

export const SUGGESTED_QUESTION_CATEGORIES: SuggestedQuestionCategory[] = [
  {
    id: "cat-exams",
    name: "Examination & Academic Regulations",
    iconName: "FileCheck",
    questions: [
      "What is the passing criteria and grade point scale for B.Tech courses?",
      "What is the procedure and deadline to apply for exam re-evaluation?",
      "What are the rules regarding supplementary and backlog examinations?",
    ],
  },
  {
    id: "cat-attendance",
    name: "Attendance & Evaluation",
    iconName: "Clock",
    questions: [
      "What is the minimum physical attendance required to sit in end-term exams?",
      "What is the medical certificate policy for attendance shortage exemptions?",
      "How is continuous internal assessment (CIA) weighted against end-term exams?",
    ],
  },
  {
    id: "cat-calendar",
    name: "Academic Calendar",
    iconName: "Calendar",
    questions: [
      "When do end-semester examinations begin for the current session?",
      "What are the scheduled winter and summer break dates?",
      "What is the last date to add or drop elective course credits?",
    ],
  },
  {
    id: "cat-hostel",
    name: "Hostel Information",
    iconName: "Building2",
    questions: [
      "What is the night curfew timing and night-out pass procedure?",
      "What are the room allotment guidelines and hostel fee payment deadlines?",
      "What electrical appliances are prohibited inside hostel premises?",
    ],
  },
  {
    id: "cat-placement",
    name: "Placement & Internships",
    iconName: "Briefcase",
    questions: [
      "What is the minimum CGPA eligibility requirement for on-campus placements?",
      "Can students accept multiple job offers under the university placement policy?",
      "What is the approval process for 8th-semester semester-long internships?",
    ],
  },
  {
    id: "cat-notices",
    name: "University Notices & Guidelines",
    iconName: "Bell",
    questions: [
      "What is the anti-ragging reporting procedure and helpline contact?",
      "How do students apply for a bonafide certificate or transcript?",
      "What are the library borrowing limits and fine charges for overdue books?",
    ],
  },
];

// ---------------------------------------------------------------------------
// 3. Mock Documents (W-07, W-08)
// ---------------------------------------------------------------------------

export const MOCK_DOCUMENTS: DocumentItem[] = [
  {
    id: "doc-001",
    title: "University Academic Regulations & Grading Handbook 2026",
    filename: "BTech_Academic_Regulations_2026.pdf",
    category: "Academic",
    pageCount: 38,
    chunkCount: 64,
    fileSize: "1.4 MB",
    status: "ready",
    uploadedBy: "System Administrator",
    createdAt: "2026-08-10T10:00:00Z",
    updatedAt: "2026-08-10T10:02:00Z",
    version: 1,
    description: "Comprehensive guide to grading systems, 10-point SGPA/CGPA formulas, probation criteria, and degree requirements.",
  },
  {
    id: "doc-002",
    title: "Hostel Rules, Code of Conduct & Mess Bylaws 2026-27",
    filename: "Hostel_Manual_and_Conduct_Rules.pdf",
    category: "Hostel",
    pageCount: 18,
    chunkCount: 28,
    fileSize: "820 KB",
    status: "ready",
    uploadedBy: "System Administrator",
    createdAt: "2026-07-28T14:30:00Z",
    updatedAt: "2026-07-28T14:31:00Z",
    version: 2,
    description: "Curfew timings, gate entry protocols, room inspection rules, mess rebate process, and disciplinary actions.",
  },
  {
    id: "doc-003",
    title: "Examination Ordinances & Backlog Registration Protocol",
    filename: "Examination_Ordinance_and_Backlog_Protocol.pdf",
    category: "Examinations",
    pageCount: 24,
    chunkCount: 42,
    fileSize: "1.1 MB",
    status: "ready",
    uploadedBy: "System Administrator",
    createdAt: "2026-09-01T09:15:00Z",
    updatedAt: "2026-09-01T09:16:00Z",
    version: 1,
    description: "Guidelines on exam paper re-evaluation, photocopy requests, backlog fees, and special examination boards.",
  },
  {
    id: "doc-004",
    title: "Training & Placement Cell Recruitment Guidelines 2026",
    filename: "TPO_Placement_Brochure_and_Rules.pdf",
    category: "Placements",
    pageCount: 15,
    chunkCount: 22,
    fileSize: "680 KB",
    status: "ready",
    uploadedBy: "System Administrator",
    createdAt: "2026-09-12T16:00:00Z",
    updatedAt: "2026-09-12T16:01:00Z",
    version: 1,
    description: "Company tiering, single-offer policy rules, dream company exemptions, and student code of conduct during drives.",
  },
  {
    id: "doc-005",
    title: "Undergraduate Admissions Prospectus & Fee Structure",
    filename: "UG_Admissions_Prospectus_2026.pdf",
    category: "Admissions",
    pageCount: 52,
    chunkCount: 98,
    fileSize: "2.8 MB",
    status: "ready",
    uploadedBy: "System Administrator",
    createdAt: "2026-06-15T11:00:00Z",
    updatedAt: "2026-06-15T11:05:00Z",
    version: 1,
    description: "Seat matrix, branch allocation rules, tuition fees, scholarship brackets, and refund policy on cancellation.",
  },
  {
    id: "doc-006",
    title: "Central Library User Policy and Borrowing Regulations",
    filename: "Library_Regulations_2026.pdf",
    category: "General",
    pageCount: 10,
    chunkCount: 14,
    fileSize: "450 KB",
    status: "ready",
    uploadedBy: "System Administrator",
    createdAt: "2026-08-18T13:45:00Z",
    updatedAt: "2026-08-18T13:46:00Z",
    version: 1,
    description: "Book checkout limits, digital repository access, late fine structures, and lost book replacement protocols.",
  },
  {
    id: "doc-007",
    title: "Annual Sports Complex Guidelines and Booking Protocol",
    filename: "Sports_Complex_Guidelines_2026.pdf",
    category: "General",
    pageCount: 8,
    chunkCount: 0,
    fileSize: "320 KB",
    status: "processing",
    uploadedBy: "System Administrator",
    createdAt: "2026-11-20T17:00:00Z",
    updatedAt: "2026-11-20T17:00:00Z",
    version: 1,
    description: "Equipment issuance rules, gymnasium timings, court reservations, and inter-college tournament norms.",
  },
  {
    id: "doc-008",
    title: "Draft Faculty Appraisal Guidelines 2027 (Corrupted Scan)",
    filename: "Faculty_Appraisal_Scan_2027.pdf",
    category: "Academic",
    pageCount: 4,
    chunkCount: 0,
    fileSize: "180 KB",
    status: "failed",
    uploadedBy: "System Administrator",
    createdAt: "2026-11-19T08:30:00Z",
    updatedAt: "2026-11-19T08:31:00Z",
    version: 1,
    description: "Failed extraction due to corrupted magic bytes in uploaded scan. Awaiting re-upload.",
  },
];

// ---------------------------------------------------------------------------
// 4. Mock Citations (W-09)
// ---------------------------------------------------------------------------

export const MOCK_CITATIONS: CitationItem[] = [
  {
    id: "cit-001",
    document: "BTech_Academic_Regulations_2026.pdf",
    page: 14,
    section: "Section 4.2 Minimum Attendance Requirement",
    snippet: "A student shall be required to maintain a minimum physical attendance of 75% in all lectures, tutorials, and practical sessions registered during the semester to be eligible for end-term examinations.",
    relevanceScore: 0.92,
  },
  {
    id: "cit-002",
    document: "BTech_Academic_Regulations_2026.pdf",
    page: 22,
    section: "Section 7.1 Grading System and CGPA Calculation",
    snippet: "Undergraduate degree classification requires cumulative grade point average (CGPA) of at least 6.0 on a 10.0 scale, with no active backlog credits at the time of program completion.",
    relevanceScore: 0.88,
  },
  {
    id: "cit-003",
    document: "Examination_Ordinance_and_Backlog_Protocol.pdf",
    page: 8,
    section: "Section 3.4 Re-evaluation and Grade Review",
    snippet: "Applications for answer script re-evaluation must be submitted within 14 calendar days from the official declaration of semester results, accompanied by a fee of Rs. 500 per theory paper.",
    relevanceScore: 0.85,
  },
  {
    id: "cit-004",
    document: "Hostel_Manual_and_Conduct_Rules.pdf",
    page: 6,
    section: "Section 2.1 Gate Timings and Night Passes",
    snippet: "All hostel residents must return to campus premises by 21:30 hrs. Night-out passes require prior digital approval from parents and the resident warden via the university portal.",
    relevanceScore: 0.81,
  },
  {
    id: "cit-005",
    document: "TPO_Placement_Brochure_and_Rules.pdf",
    page: 5,
    section: "Section 1.3 Eligibility and Single Offer Rule",
    snippet: "A student securing a job offer with an annual CTC equal to or exceeding 8.0 LPA is considered placed and shall not be permitted to participate in subsequent recruitment drives without prior waiver.",
    relevanceScore: 0.79,
  },
];

// ---------------------------------------------------------------------------
// 5. Mock Conversations (W-06)
// ---------------------------------------------------------------------------

export const MOCK_CONVERSATIONS: ConversationThread[] = [
  {
    id: "conv-101",
    title: "Attendance and Medical Leave Policy",
    userId: "usr-001",
    createdAt: "2026-11-20T14:10:00Z",
    updatedAt: "2026-11-20T14:15:00Z",
    messageCount: 4,
  },
  {
    id: "conv-102",
    title: "CGPA Requirements and Degree Classification",
    userId: "usr-001",
    createdAt: "2026-11-18T09:30:00Z",
    updatedAt: "2026-11-18T09:35:00Z",
    messageCount: 6,
  },
  {
    id: "conv-103",
    title: "Hostel Curfew and Night Out Passes",
    userId: "usr-001",
    createdAt: "2026-11-15T19:40:00Z",
    updatedAt: "2026-11-15T19:42:00Z",
    messageCount: 2,
  },
  {
    id: "conv-104",
    title: "Re-evaluation Deadline and Fee Structure",
    userId: "usr-001",
    createdAt: "2026-11-10T11:20:00Z",
    updatedAt: "2026-11-10T11:25:00Z",
    messageCount: 3,
  },
];

export const MOCK_INITIAL_MESSAGES: Record<string, ChatMessage[]> = {
  "conv-101": [
    {
      id: "msg-101",
      role: "user",
      content: "What is the minimum physical attendance required to sit in end-semester examinations?",
      createdAt: "2026-11-20T14:10:00Z",
    },
    {
      id: "msg-102",
      role: "assistant",
      content: "According to the university regulations [Source 1], all students are strictly required to maintain a minimum of 75% physical attendance across all lectures, tutorials, and laboratory sessions in each registered course to be eligible to appear in the end-semester examinations.\n\nStudents who fall between 65% and 74% attendance due to verified medical emergencies or official university representation may apply for condonation through the Dean of Student Welfare with supporting documentation.",
      createdAt: "2026-11-20T14:10:05Z",
      citations: [MOCK_CITATIONS[0]],
    },
    {
      id: "msg-103",
      role: "user",
      content: "What happens if my attendance is below 65% even with a medical certificate?",
      createdAt: "2026-11-20T14:14:00Z",
    },
    {
      id: "msg-104",
      role: "assistant",
      content: "Under no circumstances can attendance shortage below 65% be condoned [Source 1]. Students whose attendance falls below this threshold will be awarded an 'Attendance Debarred' (AD) grade and must re-register for the course in a subsequent semester.",
      createdAt: "2026-11-20T14:14:04Z",
      citations: [MOCK_CITATIONS[0]],
    },
  ],
};

// ---------------------------------------------------------------------------
// 6. Mock Analytics (W-13)
// ---------------------------------------------------------------------------

export const MOCK_ANALYTICS = {
  metrics: [
    {
      title: "Total Knowledge Queries",
      value: "14,892",
      change: "+18.4% this month",
      trend: "up" as const,
      description: "Student and faculty inquiries served via RAG pipeline.",
    },
    {
      title: "Active Documents Ingested",
      value: "68",
      change: "+6 new documents",
      trend: "up" as const,
      description: "Indexed across Qdrant vector store and MinIO S3.",
    },
    {
      title: "Avg. Retrieval Confidence",
      value: "86.4%",
      change: "+2.1% improvement",
      trend: "up" as const,
      description: "Cosine similarity across top-5 retrieved chunks.",
    },
    {
      title: "Average Latency (TTFT)",
      value: "420 ms",
      change: "-45 ms vs last week",
      trend: "up" as const,
      description: "Time to first streamed token via Groq LLM API.",
    },
  ],
  popularCategories: [
    { name: "Academic & Grading", queries: 5420, percentage: 36 },
    { name: "Examinations & Re-evaluation", queries: 3890, percentage: 26 },
    { name: "Hostel & Facilities", queries: 2410, percentage: 16 },
    { name: "Placements & Internships", queries: 1980, percentage: 13 },
    { name: "Admissions & Scholarships", queries: 1192, percentage: 9 },
  ],
  confidenceDistribution: [
    { range: "90% - 100%", count: 8420, label: "Very High" },
    { range: "75% - 89%", count: 4890, label: "High" },
    { range: "60% - 74%", count: 1210, label: "Moderate" },
    { range: "< 60% (Fallback)", count: 372, label: "Gated Fallback" },
  ],
  recentAuditLogs: [
    { id: "aud-1", action: "DOCUMENT_UPLOAD", user: "admin@university.edu", target: "BTech_Academic_Regulations_2026.pdf", timestamp: "2026-11-21 16:30" },
    { id: "aud-2", action: "VECTOR_INDEXED", user: "system", target: "BTech_Academic_Regulations_2026.pdf (64 chunks)", timestamp: "2026-11-21 16:31" },
    { id: "aud-3", action: "ROLE_CHANGE", user: "admin@university.edu", target: "faculty@university.edu -> faculty", timestamp: "2026-11-20 11:20" },
    { id: "aud-4", action: "DOCUMENT_DELETED", user: "admin@university.edu", target: "Old_Curriculum_2022.pdf", timestamp: "2026-11-19 14:15" },
  ],
};

// ---------------------------------------------------------------------------
// 7. Mock Preferences (W-17)
// ---------------------------------------------------------------------------

export interface UserPreferences {
  theme: "light" | "dark" | "system";
  fontSize: "compact" | "normal" | "spacious";
  emailNotifications: boolean;
  announcementAlerts: boolean;
  citationHighlighter: boolean;
  language: "en" | "hi";
  autoScrollChat: boolean;
}

export const DEFAULT_PREFERENCES: UserPreferences = {
  theme: "light",
  fontSize: "normal",
  emailNotifications: true,
  announcementAlerts: true,
  citationHighlighter: true,
  language: "en",
  autoScrollChat: true,
};
