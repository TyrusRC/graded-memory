import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

export type Lang = "en" | "vi";

// UI chrome only. Prompt bodies, model rationale, risk detail, audit records,
// control codes, and the verdict tokens (KEEP/REVISE/RETIRE) are evidence/data
// and are never translated.
const DICT: Record<string, { en: string; vi: string }> = {
  "nav.library": { en: "Library", vi: "Thư viện" },
  "nav.prompt": { en: "Prompt", vi: "Prompt" },
  "nav.governance": { en: "Governance", vi: "Quản trị" },
  "nav.calibration": { en: "Calibration", vi: "Hiệu chỉnh" },
  "nav.newhire": { en: "New hire", vi: "Nhân sự mới" },
  "app.loading_library": { en: "Loading library…", vi: "Đang tải thư viện…" },

  "filter.all": { en: "ALL", vi: "TẤT CẢ" },

  "lib.grade_new": {
    en: "Grade a new prompt",
    vi: "Chấm điểm một prompt mới",
  },
  "lib.paste_placeholder": {
    en: "Paste a prompt to grade it live…",
    vi: "Dán một prompt để chấm điểm trực tiếp…",
  },
  "lib.grade_live": { en: "Grade live", vi: "Chấm trực tiếp" },
  "lib.grading": { en: "Grading…", vi: "Đang chấm…" },
  "lib.grading_failed": { en: "Grading failed", vi: "Chấm điểm thất bại" },
  "lib.search_placeholder": {
    en: "Search source or text…",
    vi: "Tìm theo nguồn hoặc nội dung…",
  },
  "lib.no_match": { en: "No prompts match.", vi: "Không có prompt nào khớp." },

  "pd.select_prompt": {
    en: "Select a prompt from the Library to inspect its grade.",
    vi: "Chọn một prompt từ Thư viện để xem điểm.",
  },
  "pd.loading": { en: "Loading…", vi: "Đang tải…" },
  "pd.load_failed": {
    en: "Failed to load prompt",
    vi: "Không tải được prompt",
  },
  "pd.human_reviewed": {
    en: "Human-reviewed",
    vi: "Đã có người kiểm duyệt",
  },
  "pd.ai_graded_only": {
    en: "AI-graded only · {model}",
    vi: "Chỉ do AI chấm · {model}",
  },
  "pd.quarantined_line": {
    en: "Quarantined — excluded from reuse and new-hire handoff.",
    vi: "Đã cách ly — không được tái sử dụng hay bàn giao cho nhân sự mới.",
  },
  "pd.now_what_retire": {
    en: "Now what? Notify the owner, then capture a safe replacement. The raw prompt is flagged, never auto-sanitized.",
    vi: "Giờ làm gì? Báo cho chủ sở hữu, rồi tạo bản thay thế an toàn. Prompt gốc bị gắn cờ, không bao giờ tự động chỉnh sửa.",
  },
  "pd.now_what_revise": {
    en: "Now what? Auto-remediate to strip the risk and re-grade, or edit and re-submit.",
    vi: "Giờ làm gì? Tự động khắc phục để loại bỏ rủi ro và chấm lại, hoặc chỉnh sửa và gửi lại.",
  },
  "pd.remediate": { en: "Remediate", vi: "Khắc phục" },
  "pd.remediating": { en: "Remediating…", vi: "Đang khắc phục…" },
  "pd.remediation_failed": {
    en: "Remediation failed",
    vi: "Khắc phục thất bại",
  },
  "pd.rationale": { en: "Rationale", vi: "Lý do" },
  "pd.risks_found": { en: "Risks found", vi: "Rủi ro phát hiện" },
  "pd.control_map": { en: "Control map", vi: "Ánh xạ kiểm soát" },
  "pd.control_map_help": {
    en: "Which named governance controls this grade maps to (e.g. SR 26-2, NIST AI RMF) — the evidence an auditor asks for.",
    vi: "Điểm này ánh xạ tới những kiểm soát quản trị nào (vd. SR 26-2, NIST AI RMF) — bằng chứng mà kiểm toán viên yêu cầu.",
  },
  "pd.cannot_certify": { en: "Cannot certify.", vi: "Không thể chứng nhận." },
  "pd.cannot_certify_help": {
    en: "Not yet graded — excluded from trusted reuse until it passes the safety gate. No confident green without evidence.",
    vi: "Chưa được chấm — không được tái sử dụng tin cậy cho đến khi vượt qua cổng an toàn. Không có “đèn xanh” nếu thiếu bằng chứng.",
  },
  "pd.audit_timeline": {
    en: "Audit timeline",
    vi: "Dòng thời gian kiểm toán",
  },
  "pd.no_audit": { en: "No audit entries yet.", vi: "Chưa có mục kiểm toán nào." },

  "rubric.clarity": { en: "Clarity", vi: "Rõ ràng" },
  "rubric.context": { en: "Context", vi: "Bối cảnh" },
  "rubric.output_quality": { en: "Output quality", vi: "Chất lượng đầu ra" },
  "rubric.safety": { en: "Safety", vi: "An toàn" },

  "gov.title": {
    en: "Governance log — record of account",
    vi: "Nhật ký quản trị — hồ sơ chính thức",
  },
  "gov.events": { en: "{n} events", vi: "{n} sự kiện" },
  "gov.export_csv": { en: "Export CSV", vi: "Xuất CSV" },
  "gov.load_failed": {
    en: "Failed to load audit",
    vi: "Không tải được nhật ký",
  },
  "gov.col_prompt": { en: "Prompt", vi: "Prompt" },
  "gov.col_action": { en: "Action", vi: "Hành động" },
  "gov.col_grade": { en: "Grade", vi: "Điểm" },
  "gov.col_detail": { en: "Detail", vi: "Chi tiết" },
  "gov.col_timestamp": { en: "Timestamp", vi: "Thời điểm" },

  "cal.built_note": {
    en: "is computed live on the synthetic seed set — not examiner-validated.",
    vi: "được tính trực tiếp trên tập dữ liệu mẫu tổng hợp — chưa được kiểm toán viên xác thực.",
  },
  "cal.calibration_term": { en: "Calibration", vi: "Hiệu chỉnh" },
  "cal.calibration_help": {
    en: "Each human override, bound to the org's risk posture, tunes the grader. A competitor copies the grader in a weekend; they can't copy your accumulated verdicts — that's the moat.",
    vi: "Mỗi lần con người ghi đè, gắn với khẩu vị rủi ro của tổ chức, sẽ tinh chỉnh bộ chấm điểm. Đối thủ có thể sao chép bộ chấm trong một cuối tuần; nhưng không thể sao chép kho phán quyết tích lũy của bạn — đó là lợi thế phòng thủ.",
  },
  "cal.override_recalibrate": {
    en: "Override & recalibrate",
    vi: "Ghi đè & hiệu chỉnh",
  },
  "cal.prompt": { en: "Prompt", vi: "Prompt" },
  "cal.new_grade": { en: "New grade", vi: "Điểm mới" },
  "cal.reason": { en: "Reason", vi: "Lý do" },
  "cal.reason_placeholder": {
    en: "Why does this belong in a different bucket?",
    vi: "Vì sao mục này thuộc nhóm khác?",
  },
  "cal.apply": {
    en: "Apply override & recalibrate",
    vi: "Áp dụng ghi đè & hiệu chỉnh",
  },
  "cal.applying": { en: "Applying…", vi: "Đang áp dụng…" },
  "cal.override_failed": { en: "Override failed", vi: "Ghi đè thất bại" },
  "cal.learned_rules": { en: "Learned rules", vi: "Quy tắc đã học" },
  "cal.no_rules": {
    en: "No calibration rules yet. Apply an override to teach the grader.",
    vi: "Chưa có quy tắc hiệu chỉnh. Áp dụng một ghi đè để dạy bộ chấm điểm.",
  },
  "cal.toast": {
    en: "Learned your risk appetite — re-graded {count} similar {noun}.",
    vi: "Đã học khẩu vị rủi ro của bạn — chấm lại {count} prompt tương tự.",
  },

  "nh.certified": { en: "Certified for handoff", vi: "Đã chứng nhận để bàn giao" },
  "nh.day_one": { en: "Day one:", vi: "Ngày đầu tiên:" },
  "nh.verified_safe": {
    en: "verified-safe prompts,",
    vi: "prompt an toàn đã kiểm chứng,",
  },
  "nh.leaks": { en: "leaks.", vi: "rò rỉ." },
  "nh.everything_below": {
    en: "Everything below has been graded KEEP and is ready to hand to a new hire.",
    vi: "Mọi mục bên dưới đều được chấm KEEP và sẵn sàng bàn giao cho nhân sự mới.",
  },
  "nh.load_failed": { en: "Failed to load", vi: "Không tải được" },

  "common.loading": { en: "Loading…", vi: "Đang tải…" },
};

const LangContext = createContext<{ lang: Lang; setLang: (l: Lang) => void }>({
  lang: "en",
  setLang: () => {},
});

export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLang] = useState<Lang>(() => {
    try {
      return localStorage.getItem("gm-lang") === "vi" ? "vi" : "en";
    } catch {
      return "en";
    }
  });
  useEffect(() => {
    try {
      localStorage.setItem("gm-lang", lang);
    } catch {
      /* ignore */
    }
    document.documentElement.lang = lang;
  }, [lang]);
  return (
    <LangContext.Provider value={{ lang, setLang }}>
      {children}
    </LangContext.Provider>
  );
}

export function useLang() {
  return useContext(LangContext);
}

export type TFn = (key: string, vars?: Record<string, string | number>) => string;

export function useT(): TFn {
  const { lang } = useContext(LangContext);
  return (key, vars) => {
    const entry = DICT[key];
    let s = entry ? entry[lang] : key;
    if (vars) {
      for (const [k, v] of Object.entries(vars)) {
        s = s.replace(`{${k}}`, String(v));
      }
    }
    return s;
  };
}
