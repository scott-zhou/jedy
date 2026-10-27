import java.util.*;

public class Main {
    interface Shape { double area(); default String kind() { return "shape"; } }
    static class Circle implements Shape {
        double r; Circle(double r) { this.r = r; }
        public double area() { return Math.PI * r * r; }
    }
    static class Square implements Shape {
        int s; Square(int s) { this.s = s; }
        public double area() { return s * s; }
        public String kind() { return "square"; }
    }

    static long fib(int n) { return n < 2 ? n : fib(n - 1) + fib(n - 2); }

    static String day(int d) {
        switch (d) {
            case 1: return "Mon";
            case 2: return "Tue";
            case 100: return "Hundred";
            default: return "Other";
        }
    }

    public static void main(String[] args) {
        System.out.println("fib(20) = " + fib(20));
        long big = Long.MAX_VALUE;
        System.out.println("overflow: " + (big + 1) + " " + (Integer.MAX_VALUE + 1));
        System.out.println("div: " + (-7 / 2) + " " + (-7 % 2) + " " + (7L >>> 1) + " " + (-1 >>> 28));
        System.out.println("double: " + (1.0 / 3) + " float: " + (1.0f / 3) + " " + (double) 0.1f);
        System.out.println("chars: " + (char) ('a' + 1) + " " + (int) 'z');
        int[] arr = {5, 3, 9, 1, 7};
        Arrays.sort(arr);
        System.out.println("sorted: " + Arrays.toString(arr));
        List<String> list = new ArrayList<>();
        for (int i = 0; i < 5; i++) list.add("item" + i);
        Collections.reverse(list);
        System.out.println(list);
        Map<String, Integer> map = new HashMap<>();
        for (String w : "the quick brown fox jumps over the lazy dog the end".split(" "))
            map.put(w, map.getOrDefault(w, 0) + 1);
        System.out.println("the=" + map.get("the") + " size=" + map.size());
        Shape[] shapes = {new Circle(1.5), new Square(3)};
        for (Shape s : shapes) System.out.println(s.kind() + " " + (Math.round(s.area() * 1000) / 1000.0));
        System.out.println(day(1) + day(2) + day(100) + day(5));
        try {
            Object o = "str";
            Integer x = (Integer) o;
        } catch (ClassCastException e) {
            System.out.println("caught CCE");
        }
        try {
            int[] a = new int[2];
            a[5] = 1;
        } catch (ArrayIndexOutOfBoundsException e) {
            System.out.println("caught " + e.getMessage());
        } finally {
            System.out.println("finally");
        }
        try {
            System.out.println(10 / (args.length));
        } catch (ArithmeticException e) {
            System.out.println("caught " + e);
        }
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < 3; i++) sb.append(i).append(',');
        System.out.println(sb.reverse());
        System.out.println(String.valueOf(3.14159) + " " + Integer.toHexString(255) + " " + Long.parseLong("-123456789012"));
        System.out.println("中文 unicode ✓ " + "abc".hashCode() + " " + "héllo".toUpperCase());
        int[][] grid = new int[3][4];
        grid[2][3] = 7;
        System.out.println(grid.length + "x" + grid[0].length + " " + grid[2][3]);
        System.err.println("to stderr");
        throw new IllegalStateException("boom");
    }
}
