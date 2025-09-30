```typescript
import React, { useState, useMemo, useRef } from 'react';
import { Eye, EyeOff, Layout, Search, Download, FileText, MousePointer } from 'lucide-react';
import { Switch } from '@/components/ui/switch';
import { Button } from '@/components/ui/button';
import { Tabs, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel, DropdownMenuSeparator, DropdownMenuTrigger } from '@/components/ui/dropdown-menu';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

const mockData = {
  source_documents: [
    {
      doc_id: "src_001",
      metadata: { title: "AI 윤리 가이드라인", doc_type: "정책 문서" },
      content: {
        lines: [
          { line_num: 1, text: "AI 윤리 원칙의 중요성", sentence_ids: ["src_001_s1"] },
          { line_num: 2, text: "인공지능 기술이 사회 전반에 미치는 영향이 커지면서 윤리적 고려가 필수적입니다. AI 시스템은 투명하고", sentence_ids: ["src_001_s2", "src_001_s3"] },
          { line_num: 3, text: "공정해야 하며, 인간의 가치를 존중해야 합니다. 편향성 문제는 특히 중요한 이슈입니다.", sentence_ids: ["src_001_s3", "src_001_s4"] },
          { line_num: 4, text: "", sentence_ids: [] },
          { line_num: 5, text: "데이터 프라이버시와 보안", sentence_ids: ["src_001_s5"] },
          { line_num: 6, text: "개인정보 보호는 AI 개발의 핵심 요소입니다. 사용자 데이터는 적법하게 수집되어야 하며, 명확한 동의 절차가", sentence_ids: ["src_001_s6", "src_001_s7"] },
          { line_num: 7, text: "필요합니다. 데이터 암호화와 익명화 기술을 활용해야 합니다.", sentence_ids: ["src_001_s7", "src_001_s8"] },
        ],
        sentences: [
          { id: "src_001_s1", text: "AI 윤리 원칙의 중요성", lines: [1], doc_id: "src_001" },
          { id: "src_001_s2", text: "인공지능 기술이 사회 전반에 미치는 영향이 커지면서 윤리적 고려가 필수적입니다.", lines: [2], doc_id: "src_001" },
          { id: "src_001_s3", text: "AI 시스템은 투명하고 공정해야 하며, 인간의 가치를 존중해야 합니다.", lines: [2, 3], doc_id: "src_001" },
          { id: "src_001_s4", text: "편향성 문제는 특히 중요한 이슈입니다.", lines: [3], doc_id: "src_001" },
          { id: "src_001_s5", text: "데이터 프라이버시와 보안", lines: [5], doc_id: "src_001" },
          { id: "src_001_s6", text: "개인정보 보호는 AI 개발의 핵심 요소입니다.", lines: [6], doc_id: "src_001" },
          { id: "src_001_s7", text: "사용자 데이터는 적법하게 수집되어야 하며, 명확한 동의 절차가 필요합니다.", lines: [6, 7], doc_id: "src_001" },
          { id: "src_001_s8", text: "데이터 암호화와 익명화 기술을 활용해야 합니다.", lines: [7], doc_id: "src_001" },
        ]
      }
    },
    {
      doc_id: "src_002",
      metadata: { title: "AI 보안 표준", doc_type: "기술 표준" },
      content: {
        lines: [
          { line_num: 1, text: "AI 시스템 보안 요구사항", sentence_ids: ["src_002_s1"] },
          { line_num: 2, text: "AI 시스템은 다양한 보안 위협에 노출되어 있습니다. 모델 탈취, 데이터 오염, 적대적 공격 등에", sentence_ids: ["src_002_s2", "src_002_s3"] },
          { line_num: 3, text: "대비한 보안 체계가 필요합니다.", sentence_ids: ["src_002_s3"] },
          { line_num: 4, text: "", sentence_ids: [] },
          { line_num: 5, text: "접근 제어와 권한 관리가 핵심입니다. 정기적인 보안 감사를 통해 취약점을 파악해야 합니다.", sentence_ids: ["src_002_s4", "src_002_s5"] },
        ],
        sentences: [
          { id: "src_002_s1", text: "AI 시스템 보안 요구사항", lines: [1], doc_id: "src_002" },
          { id: "src_002_s2", text: "AI 시스템은 다양한 보안 위협에 노출되어 있습니다.", lines: [2], doc_id: "src_002" },
          { id: "src_002_s3", text: "모델 탈취, 데이터 오염, 적대적 공격 등에 대비한 보안 체계가 필요합니다.", lines: [2, 3], doc_id: "src_002" },
          { id: "src_002_s4", text: "접근 제어와 권한 관리가 핵심입니다.", lines: [5], doc_id: "src_002" },
          { id: "src_002_s5", text: "정기적인 보안 감사를 통해 취약점을 파악해야 합니다.", lines: [5], doc_id: "src_002" },
        ]
      }
    }
  ],
  processed_document: {
    doc_id: "proc_001",
    source_doc_ids: ["src_001", "src_002"],
    metadata: { title: "AI 윤리 및 보안 종합 요약", processing_type: "summary" },
    content: {
      lines: [
        { line_num: 1, text: "AI 윤리와 보안의 기본 방향", sentence_ids: ["proc_s1"] },
        { line_num: 2, text: "AI 기술의 사회적 영향이 증가하면서 윤리적 고려와 투명성, 공정성이 필수적입니다. 편향성 문제 해결이", sentence_ids: ["proc_s2", "proc_s3"] },
        { line_num: 3, text: "핵심 과제로 부상했습니다.", sentence_ids: ["proc_s3"] },
        { line_num: 4, text: "", sentence_ids: [] },
        { line_num: 5, text: "프라이버시와 보안 체계", sentence_ids: ["proc_s4"] },
        { line_num: 6, text: "개인정보 보호와 데이터 수집이 중요합니다. 암호화 기술 활용 및 접근 권한 관리와", sentence_ids: ["proc_s5", "proc_s6"] },
        { line_num: 7, text: "정기 보안 감사가 필수입니다.", sentence_ids: ["proc_s6"] },
      ],
      sentences: [
        { id: "proc_s1", text: "AI 윤리와 보안의 기본 방향", lines: [1] },
        { id: "proc_s2", text: "AI 기술의 사회적 영향이 증가하면서 윤리적 고려와 투명성, 공정성이 필수적입니다.", lines: [2] },
        { id: "proc_s3", text: "편향성 문제 해결이 핵심 과제로 부상했습니다.", lines: [2, 3] },
        { id: "proc_s4", text: "프라이버시와 보안 체계", lines: [5] },
        { id: "proc_s5", text: "개인정보 보호와 데이터 수집이 중요합니다.", lines: [6] },
        { id: "proc_s6", text: "암호화 기술 활용 및 접근 권한 관리와 정기 보안 감사가 필수입니다.", lines: [6, 7] },
      ]
    }
  },
  mappings: {
    summary_to_source: {
      "proc_s1": ["src_001_s1"],
      "proc_s2": ["src_001_s2", "src_001_s3"],
      "proc_s3": ["src_001_s4"],
      "proc_s4": ["src_001_s5", "src_002_s1"],
      "proc_s5": ["src_001_s6", "src_001_s7"],
      "proc_s6": ["src_001_s8", "src_002_s4", "src_002_s5"]
    },
    source_to_summary: {
      "src_001_s1": ["proc_s1"], "src_001_s2": ["proc_s2"], "src_001_s3": ["proc_s2"],
      "src_001_s4": ["proc_s3"], "src_001_s5": ["proc_s4"], "src_001_s6": ["proc_s5"],
      "src_001_s7": ["proc_s5"], "src_001_s8": ["proc_s6"],
      "src_002_s1": ["proc_s4"], "src_002_s4": ["proc_s6"], "src_002_s5": ["proc_s6"]
    }
  }
};

const allSourceSentences = mockData.source_documents.reduce((acc, doc) => {
  doc.content.sentences.forEach(s => { acc[s.id] = s; });
  return acc;
}, {});

const parseLineSegments = (line, sentences) => {
  if (!line.sentence_ids.length) return [{ text: line.text, sentenceId: null, isPartial: false }];
  const segments = [];
  let pos = 0;
  line.sentence_ids.forEach((id) => {
    const sent = sentences.find(s => s.id === id);
    if (!sent) return;
    const idx = line.text.indexOf(sent.text.trim().split(' ')[0], pos);
    const start = idx === -1 ? pos : idx;
    if (start > pos) segments.push({ text: line.text.substring(pos, start), sentenceId: null, isPartial: false });
    const end = Math.min(start + sent.text.length, line.text.length);
    segments.push({ text: line.text.substring(start, end || line.text.length), sentenceId: id, isPartial: sent.lines.length > 1 });
    pos = end || line.text.length;
  });
  if (pos < line.text.length) segments.push({ text: line.text.substring(pos), sentenceId: null, isPartial: false });
  return segments.length ? segments : [{ text: line.text, sentenceId: null, isPartial: false }];
};

const SentenceSegment = ({ segment, isHighlighted, isHovered, onMouseEnter, onMouseLeave }) => {
  if (!segment.sentenceId) return <span className="opacity-50">{segment.text}</span>;
  return (
    <span
      className={`inline cursor-pointer rounded px-0.5 py-px transition-all ${
        isHovered ? 'bg-blue-600 text-white font-medium shadow-md' : 
        isHighlighted ? 'bg-amber-100 shadow-sm' : ''
      }`}
      onMouseEnter={onMouseEnter}
      onMouseLeave={onMouseLeave}
    >
      {segment.text}
      {segment.isPartial && <span className="text-gray-400 text-xs ml-0.5 opacity-60">↵</span>}
    </span>
  );
};

const LineView = ({ line, sentences, highlightedSentences, hoveredSentence, onSentenceHover, onSentenceLeave, showLineNumbers }) => {
  const segments = useMemo(() => parseLineSegments(line, sentences), [line, sentences]);
  return (
    <div className="flex py-0.5 min-h-[24px]">
      {showLineNumbers && <div className="w-11 text-right pr-4 text-gray-400 select-none text-sm">{line.line_num}</div>}
      <div className="flex-1 whitespace-pre-wrap break-words font-mono text-sm leading-relaxed">
        {segments.map((seg, i) => (
          <SentenceSegment
            key={i}
            segment={seg}
            isHighlighted={seg.sentenceId && highlightedSentences.includes(seg.sentenceId)}
            isHovered={seg.sentenceId && hoveredSentence === seg.sentenceId}
            onMouseEnter={(e) => seg.sentenceId && onSentenceHover(seg.sentenceId, e)}
            onMouseLeave={onSentenceLeave}
          />
        ))}
      </div>
    </div>
  );
};

const DocumentPanel = ({ document, type, highlightedSentences, hoveredSentence, onSentenceHover, onSentenceLeave, showLineNumbers, searchTerm }) => {
  const filteredLines = useMemo(() => {
    if (!searchTerm) return document.content.lines;
    return document.content.lines.filter(line => line.text.toLowerCase().includes(searchTerm.toLowerCase()));
  }, [document.content.lines, searchTerm]);
  
  return (
    <Card>
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <div className="flex flex-col gap-1">
            <CardTitle className="text-lg">{document.metadata.title}</CardTitle>
            {document.source_doc_ids && (
              <div className="flex items-center gap-2 text-xs text-gray-500">
                <FileText size={12} />
                <span>{document.source_doc_ids.length}개 문서 요약</span>
              </div>
            )}
          </div>
          <Badge variant={type === 'source' ? 'default' : 'secondary'}>
            {type === 'source' ? '원본 문서' : '처리 문서'}
          </Badge>
        </div>
      </CardHeader>
      <CardContent className="pt-0">
        <div className="max-h-[65vh] overflow-y-auto p-2">
          {filteredLines.map((line) => (
            <LineView
              key={line.line_num}
              line={line}
              sentences={document.content.sentences}
              highlightedSentences={highlightedSentences}
              hoveredSentence={hoveredSentence}
              onSentenceHover={onSentenceHover}
              onSentenceLeave={onSentenceLeave}
              showLineNumbers={showLineNumbers}
            />
          ))}
        </div>
      </CardContent>
    </Card>
  );
};

const SourceDocumentSelector = ({ documents, selectedDoc, onSelect }) => {
  return (
    <Tabs value={selectedDoc.doc_id} onValueChange={(val) => onSelect(documents.find(d => d.doc_id === val))}>
      <TabsList className="w-full">
        {documents.map(doc => (
          <TabsTrigger key={doc.doc_id} value={doc.doc_id} className="flex-1">
            {doc.metadata.title}
          </TabsTrigger>
        ))}
      </TabsList>
    </Tabs>
  );
};

const App = () => {
  const [layout, setLayout] = useState('horizontal');
  const [hoveredSentence, setHoveredSentence] = useState(null);
  const [highlightedSentences, setHighlightedSentences] = useState([]);
  const [previewContent, setPreviewContent] = useState(null);
  const [previewPosition, setPreviewPosition] = useState({ x: 0, y: 0 });
  const [showLineNumbers, setShowLineNumbers] = useState(true);
  const [activeDocument, setActiveDocument] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [selectedSourceDoc, setSelectedSourceDoc] = useState(mockData.source_documents[0]);
  
  const hoverTimeoutRef = useRef(null);
  const previewRef = useRef(null);

  const handleSentenceHover = (sentenceId, documentType, event) => {
    // 기존 타이머 취소
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
    }

    setHoveredSentence(sentenceId);
    setActiveDocument(documentType);
    
    const mappingKey = documentType === 'source' ? 'source_to_summary' : 'summary_to_source';
    const relatedIds = mockData.mappings[mappingKey][sentenceId] || [];
    setHighlightedSentences(relatedIds);

    let previewSentences = [];
    if (documentType === 'source') {
      previewSentences = relatedIds.map(id => mockData.processed_document.content.sentences.find(s => s.id === id)).filter(Boolean);
    } else {
      previewSentences = relatedIds.map(id => allSourceSentences[id]).filter(Boolean);
    }

    const groupedByDoc = previewSentences.reduce((acc, sent) => {
      const docId = sent.doc_id || 'processed';
      if (!acc[docId]) acc[docId] = [];
      acc[docId].push(sent);
      return acc;
    }, {});

    setPreviewContent({
      sentencesByDoc: groupedByDoc,
      sourceType: documentType === 'source' ? 'processed' : 'source'
    });

    if (event) {
      const rect = event.currentTarget.getBoundingClientRect();
      const centerX = rect.left + (rect.width / 2);
      setPreviewPosition({
        x: centerX,
        y: rect.bottom + window.scrollY + 8
      });
    }
  };

  const handleSentenceLeave = () => {
    // 약간의 지연을 두고 닫기 (프리뷰로 마우스 이동 가능하도록)
    hoverTimeoutRef.current = setTimeout(() => {
      setHoveredSentence(null);
      setHighlightedSentences([]);
      setPreviewContent(null);
      setActiveDocument(null);
    }, 200);
  };

  const handlePreviewEnter = () => {
    // 프리뷰에 마우스가 올라오면 타이머 취소
    if (hoverTimeoutRef.current) {
      clearTimeout(hoverTimeoutRef.current);
    }
  };

  const handlePreviewLeave = () => {
    // 프리뷰에서 마우스가 벗어나면 닫기
    setHoveredSentence(null);
    setHighlightedSentences([]);
    setPreviewContent(null);
    setActiveDocument(null);
  };

  const handleSentenceClick = (sentenceId) => {
    const sentence = allSourceSentences[sentenceId];
    if (sentence && sentence.doc_id) {
      const doc = mockData.source_documents.find(d => d.doc_id === sentence.doc_id);
      if (doc) {
        setSelectedSourceDoc(doc);
        // 잠시 후 해당 문장 하이라이트
        setTimeout(() => {
          setHoveredSentence(sentenceId);
          setHighlightedSentences([sentenceId]);
        }, 100);
      }
    }
  };

  const getDocumentTitle = (docId) => {
    if (docId === 'processed') return mockData.processed_document.metadata.title;
    const doc = mockData.source_documents.find(d => d.doc_id === docId);
    return doc ? doc.metadata.title : docId;
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="sticky top-0 z-50 bg-white border-b px-6 py-4 backdrop-blur">
        <div className="max-w-7xl mx-auto flex items-center justify-between gap-4 flex-wrap">
          <div className="flex items-center gap-6 flex-wrap">
            <Tabs value={layout} onValueChange={setLayout}>
              <TabsList>
                <TabsTrigger value="horizontal" className="flex items-center gap-2">
                  <Layout size={16} />좌우 분할
                </TabsTrigger>
                <TabsTrigger value="vertical" className="flex items-center gap-2">
                  <Layout size={16} className="rotate-90" />상하 분할
                </TabsTrigger>
              </TabsList>
            </Tabs>
            <div className="flex items-center gap-3">
              <Switch id="lines" checked={showLineNumbers} onCheckedChange={setShowLineNumbers} />
              <Label htmlFor="lines" className="flex items-center gap-2 cursor-pointer">
                {showLineNumbers ? <Eye size={16} /> : <EyeOff size={16} />}라인 번호
              </Label>
            </div>
            <div className="relative w-64">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" size={16} />
              <Input type="text" placeholder="문서 검색..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="pl-9" />
            </div>
          </div>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="icon"><Download size={16} /></Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>내보내기</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem>PDF로 저장</DropdownMenuItem>
              <DropdownMenuItem>HTML로 저장</DropdownMenuItem>
              <DropdownMenuItem>JSON 데이터</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      <div className="max-w-7xl mx-auto p-6">
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-6 text-sm">
          <strong>💡 사용 방법:</strong> 문장에 마우스를 올리면 관련 문장들이 하이라이트되고 상세 정보가 표시됩니다. 
          <span className="ml-2 text-blue-700">프리뷰에서 문장을 클릭하면 해당 소스 문서로 전환됩니다.</span>
        </div>

        <div className="mb-4">
          <SourceDocumentSelector 
            documents={mockData.source_documents} 
            selectedDoc={selectedSourceDoc}
            onSelect={setSelectedSourceDoc}
          />
        </div>

        <div className={`grid gap-6 ${layout === 'horizontal' ? 'grid-cols-2' : 'grid-rows-2'}`}>
          <DocumentPanel
            document={selectedSourceDoc}
            type="source"
            highlightedSentences={activeDocument === 'processed' ? highlightedSentences : []}
            hoveredSentence={activeDocument === 'source' ? hoveredSentence : null}
            onSentenceHover={(id, e) => handleSentenceHover(id, 'source', e)}
            onSentenceLeave={handleSentenceLeave}
            showLineNumbers={showLineNumbers}
            searchTerm={searchTerm}
          />
          <DocumentPanel
            document={mockData.processed_document}
            type="processed"
            highlightedSentences={activeDocument === 'source' ? highlightedSentences : []}
            hoveredSentence={activeDocument === 'processed' ? hoveredSentence : null}
            onSentenceHover={(id, e) => handleSentenceHover(id, 'processed', e)}
            onSentenceLeave={handleSentenceLeave}
            showLineNumbers={showLineNumbers}
            searchTerm={searchTerm}
          />
        </div>

        {previewContent && Object.keys(previewContent.sentencesByDoc).length > 0 && (
          <div 
            ref={previewRef}
            className="fixed w-[450px] max-w-[90vw] bg-white border rounded-lg shadow-2xl z-50 animate-in fade-in duration-200"
            style={{ 
              left: `${Math.max(10, Math.min(previewPosition.x - 225, window.innerWidth - 460))}px`,
              top: `${previewPosition.y}px` 
            }}
            onMouseEnter={handlePreviewEnter}
            onMouseLeave={handlePreviewLeave}
          >
            <div className="p-4 border-b bg-gradient-to-r from-blue-50 to-purple-50">
              <h4 className="font-semibold text-sm flex items-center gap-2">
                {previewContent.sourceType === 'source' ? '📄 관련 원본 문장' : '📝 관련 요약 문장'}
                <Badge variant="secondary">{Object.values(previewContent.sentencesByDoc).flat().length}개</Badge>
              </h4>
            </div>
            <div className="max-h-96 overflow-y-auto">
              {Object.entries(previewContent.sentencesByDoc).map(([docId, sentences]) => (
                <div key={docId} className="border-b last:border-0">
                  <div className="px-4 py-2 bg-gray-50 text-xs font-semibold text-gray-600 flex items-center gap-2">
                    <FileText size={12} />
                    {getDocumentTitle(docId)}
                  </div>
                  <div className="p-4 space-y-3">
                    {sentences.map((sentence, idx) => (
                      <div 
                        key={sentence.id} 
                        className="flex gap-2 hover:bg-blue-50 p-2 -m-2 rounded cursor-pointer transition-colors group"
                        onClick={() => handleSentenceClick(sentence.id)}
                      >
                        <span className="text-gray-400 font-semibold text-xs min-w-[20px]">{idx + 1}.</span>
                        <div className="flex-1">
                          <span className="text-sm leading-relaxed">{sentence.text}</span>
                          <div className="flex items-center gap-1 text-xs text-blue-600 opacity-0 group-hover:opacity-100 transition-opacity mt-1">
                            <MousePointer size={12} />
                            <span>클릭하여 이동</span>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default App;
```
