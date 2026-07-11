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
  "nav.capability": { en: "Capability", vi: "Năng lực" },
  "app.loading_library": { en: "Loading library…", vi: "Đang tải thư viện…" },

  "filter.all": { en: "ALL", vi: "TẤT CẢ" },

  "kind.prompt": { en: "Prompt", vi: "Prompt" },
  "kind.workflow": { en: "Workflow", vi: "Quy trình" },
  "kind.agent": { en: "Agent", vi: "Agent" },

  "lib.grade_new": {
    en: "Grade a new prompt",
    vi: "Chấm điểm một prompt mới",
  },
  "lib.paste_placeholder": {
    en: "Paste a prompt to grade it live…",
    vi: "Dán một prompt để chấm điểm trực tiếp…",
  },
  "lib.grade_live": { en: "Grade live", vi: "Chấm trực tiếp" },
  "lib.kind": { en: "Kind", vi: "Loại" },
  "lib.context_label": {
    en: "Context (why it worked / when to use)",
    vi: "Bối cảnh (vì sao hiệu quả / khi nào dùng)",
  },
  "lib.context_placeholder": {
    en: "Optional — note why this worked or when to use it…",
    vi: "Tùy chọn — ghi vì sao hiệu quả hoặc khi nào dùng…",
  },
  "lib.grading": { en: "Grading…", vi: "Đang chấm…" },
  "lib.grading_failed": { en: "Grading failed", vi: "Chấm điểm thất bại" },
  "lib.search_placeholder": {
    en: "Search source or text…",
    vi: "Tìm theo nguồn hoặc nội dung…",
  },
  "lib.no_match": { en: "No prompts match.", vi: "Không có prompt nào khớp." },

  "reuse.title": {
    en: "Prior art for this task",
    vi: "Kết quả có sẵn cho tác vụ này",
  },
  "reuse.help": {
    en: "Verified assets the org already built for similar work — reuse before you rebuild.",
    vi: "Những tài sản đã kiểm chứng mà tổ chức đã xây cho công việc tương tự — tái sử dụng trước khi làm lại.",
  },
  "reuse.searching": {
    en: "Searching prior art…",
    vi: "Đang tìm kết quả có sẵn…",
  },
  "reuse.none": {
    en: "No prior art found — this looks like new capability.",
    vi: "Không tìm thấy kết quả có sẵn — đây có vẻ là năng lực mới.",
  },
  "reuse.match": { en: "{score}% match", vi: "khớp {score}%" },

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
  "pd.policy_forced": {
    en: "Verdict set by the deterministic safety gate — a high-severity {category}, not the model's call.",
    vi: "Phán quyết do cổng an toàn tất định quyết định — rủi ro {category} mức cao, không phải do mô hình.",
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
  "pd.context": {
    en: "Why it worked / when to use",
    vi: "Vì sao hiệu quả / khi nào dùng",
  },
  "pd.rationale": { en: "Rationale", vi: "Lý do" },
  "pd.foreseen_actions": {
    en: "Foreseen agent actions",
    vi: "Hành động agent dự đoán",
  },
  "pd.foreseen_actions_help": {
    en: "The step-by-step action chain the agentic Judge reasoned an autonomous agent would execute if it ran this prompt — the risk is in what it would DO, not just the wording.",
    vi: "Chuỗi hành động từng bước mà Bộ chấm agentic suy luận rằng một agent tự động sẽ thực thi nếu chạy prompt này — rủi ro nằm ở việc nó SẼ LÀM gì, không chỉ ở câu chữ.",
  },
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
  "nh.handoff_title": {
    en: "When someone leaves, their memory stays",
    vi: "Khi một người rời đi, ký ức của họ vẫn ở lại",
  },
  "nh.handoff_intro": {
    en: "Every verified-safe AI asset a departing employee built transfers to their replacement on day one — no lost prompts, no leaked ones.",
    vi: "Mọi tài sản AI an toàn đã kiểm chứng mà nhân viên rời đi tạo ra sẽ chuyển cho người thay thế ngay ngày đầu — không mất prompt, không rò rỉ.",
  },
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

  "cap.title": { en: "Capability map", vi: "Bản đồ năng lực" },
  "cap.intro": {
    en: "Where organizational AI capability is growing, duplicated, or missing.",
    vi: "Nơi năng lực AI của tổ chức đang tăng trưởng, trùng lặp, hoặc thiếu hụt.",
  },
  "cap.load_failed": {
    en: "Failed to load analytics",
    vi: "Không tải được phân tích",
  },
  "cap.by_kind": { en: "Assets by kind", vi: "Tài sản theo loại" },
  "cap.coverage": { en: "Coverage by tag", vi: "Độ phủ theo thẻ" },
  "cap.col_tag": { en: "Tag", vi: "Thẻ" },
  "cap.col_total": { en: "Total", vi: "Tổng" },
  "cap.duplicates": { en: "Duplicated capability", vi: "Năng lực trùng lặp" },
  "cap.duplicates_none": {
    en: "No duplication detected.",
    vi: "Không phát hiện trùng lặp.",
  },
  "cap.duplicates_note": {
    en: "These assets overlap heavily — consolidate into one source of truth.",
    vi: "Các tài sản này trùng lặp nhiều — hãy hợp nhất thành một nguồn duy nhất.",
  },
  "cap.gaps": { en: "Missing capability", vi: "Năng lực thiếu hụt" },
  "cap.gaps_none": {
    en: "No coverage gaps — every tag has a verified KEEP asset.",
    vi: "Không có lỗ hổng — mọi thẻ đều có tài sản KEEP đã kiểm chứng.",
  },
  "cap.gaps_note": {
    en: "Tags with assets but zero graded-KEEP coverage.",
    vi: "Các thẻ có tài sản nhưng chưa có mục KEEP nào được chấm.",
  },
  "cap.growth": { en: "Grading activity", vi: "Hoạt động chấm điểm" },
  "cap.growth_none": {
    en: "No grading activity recorded yet.",
    vi: "Chưa ghi nhận hoạt động chấm điểm.",
  },
  "cap.graded_count": { en: "{n} graded", vi: "{n} lần chấm" },
  "cap.match": { en: "{score}% overlap", vi: "trùng {score}%" },

  "common.loading": { en: "Loading…", vi: "Đang tải…" },

  "llm.checking": { en: "Checking…", vi: "Đang kiểm tra…" },
  "llm.live": { en: "Live", vi: "Trực tiếp" },
  "llm.offline": { en: "Offline", vi: "Ngoại tuyến" },
  "llm.unreachable": { en: "Unreachable", vi: "Không kết nối" },
  "llm.title": { en: "Live grading (your key)", vi: "Chấm trực tiếp (khóa của bạn)" },
  "llm.intro": {
    en: "Bring your own key for live agentic grading — pick a provider, or use OpenRouter to reach any model (Claude, Gemini, Llama, 300+). Leave blank to grade deterministically offline.",
    vi: "Dùng khóa của bạn để chấm agentic trực tiếp — chọn nhà cung cấp, hoặc dùng OpenRouter để truy cập mọi mô hình (Claude, Gemini, Llama, hơn 300). Để trống sẽ chấm tất định ngoại tuyến.",
  },
  "llm.provider": { en: "Provider", vi: "Nhà cung cấp" },
  "llm.base_url": { en: "Base URL", vi: "Base URL" },
  "llm.api_key": { en: "API key", vi: "Khóa API" },
  "llm.model": { en: "Model", vi: "Mô hình" },
  "llm.save_test": { en: "Save & test", vi: "Lưu & kiểm tra" },
  "llm.status_online": {
    en: "Connected — grading live with {model}.",
    vi: "Đã kết nối — chấm trực tiếp bằng {model}.",
  },
  "llm.status_error": {
    en: "Not reachable ({error}). Still grading safely offline.",
    vi: "Không kết nối được ({error}). Vẫn chấm an toàn ngoại tuyến.",
  },
  "llm.status_offline": {
    en: "No key set — grading deterministically offline. Add a provider for live agentic grading.",
    vi: "Chưa đặt khóa — chấm tất định ngoại tuyến. Thêm nhà cung cấp để chấm agentic trực tiếp.",
  },
  "llm.privacy": {
    en: "Your key stays in this browser and is sent per-request only to grade — never stored or logged on the server. Prompts are redacted before any model call.",
    vi: "Khóa của bạn chỉ nằm trong trình duyệt này và chỉ gửi theo từng yêu cầu để chấm — không lưu hay ghi log trên máy chủ. Prompt được che thông tin nhạy cảm trước mọi lần gọi mô hình.",
  },
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
