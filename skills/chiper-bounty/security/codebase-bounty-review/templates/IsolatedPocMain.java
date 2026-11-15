// Driver skeleton for an isolated-compile PoC (see references/isolated-compile-poc.md).
// Copy the target class(es) VERBATIM into poc/src/<declared-package-path>/ first, then edit this file.
// Compile/run:  javac -d out $(find src -name '*.java') && java -cp out poc.Main
package poc;

import java.util.List;

public final class IsolatedPocMain {

    public static void main(String[] args) {
        int failures = 0;

        // --- Call the VERBATIM production class here (adjust names to the target) ---
        // e.g. final var target = SomeProductionClass.INSTANCE;
        //      final boolean bypassed = target.check(attackerInput);
        //      System.out.println("[1] check(attackerInput) = " + bypassed);
        //      if (!bypassed) failures++;

        // Pattern for "verification is a no-op": feed intentionally-invalid input and show it is accepted.
        // Pattern for "gate is trivially satisfiable": replicate the exact guard arithmetic and show it passes.

        System.out.println();
        if (failures == 0) {
            System.out.println("PROVEN: <one-line statement of the bypass>");
        } else {
            System.out.println("PoC did NOT reproduce (" + failures + " check(s) failed).");
            System.exit(1);
        }
    }

    private IsolatedPocMain() {}
}
