// 이미지에 박힌 글씨 읽기 (macOS Vision, 한국어+영어, 무료·로컬). 2026-11-11 레퍼런스 검색용.
// 사용: ocr <이미지...>  → 줄마다 {"f":파일,"t":글씨} JSON
import Foundation
import Vision
import AppKit
for p in CommandLine.arguments.dropFirst() {
  autoreleasepool {
    guard let im = NSImage(contentsOfFile: p), let cg = im.cgImage(forProposedRect: nil, context: nil, hints: nil) else { return }
    let rq = VNRecognizeTextRequest()
    rq.recognitionLanguages = ["ko-KR", "en-US"]; rq.recognitionLevel = .accurate; rq.usesLanguageCorrection = true
    try? VNImageRequestHandler(cgImage: cg, options: [:]).perform([rq])
    let t = (rq.results ?? []).compactMap { $0.topCandidates(1).first?.string }.joined(separator: " ")
    if let d = try? JSONSerialization.data(withJSONObject: ["f": (p as NSString).lastPathComponent, "t": t]), let s = String(data: d, encoding: .utf8) { print(s) }
  }
}
