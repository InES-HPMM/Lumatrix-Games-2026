// Prints word vectors from Apple's built-in English word embedding, one per
// line: word, a tab, then 300 numbers. For each word in the keyword file it
// also prints its nearest neighbours, so the model learns related words
// ("storm" next to "rain") that no symbol lists.
//
//     swift model/export_vectors.swift keywords.txt 120 [extra-words.txt]

import Foundation
import NaturalLanguage

let arguments = CommandLine.arguments
guard arguments.count >= 3, let neighbours = Int(arguments[2]) else {
    FileHandle.standardError.write("usage: export_vectors.swift keywords.txt neighbours [extra-words.txt]\n".data(using: .utf8)!)
    exit(2)
}
guard let embedding = NLEmbedding.wordEmbedding(for: .english) else {
    FileHandle.standardError.write("This Mac has no English word embedding.\n".data(using: .utf8)!)
    exit(1)
}

func words(in path: String) throws -> [String] {
    try String(contentsOfFile: path, encoding: .utf8).split(whereSeparator: \.isNewline).map(String.init)
}

var seen = Set<String>()
func emit(_ word: String) {
    guard !seen.contains(word), let vector = embedding.vector(for: word) else { return }
    seen.insert(word)
    print(word + "\t" + vector.map { String(format: "%.5f", $0) }.joined(separator: " "))
}

for keyword in try words(in: arguments[1]) {
    emit(keyword)
    for (neighbour, _) in embedding.neighbors(for: keyword, maximumCount: neighbours) {
        emit(neighbour)
    }
}
if arguments.count > 3 {
    for word in try words(in: arguments[3]) {
        emit(word)
    }
}
